#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Functions for the Keepers query. Extra file for better readability.

import logging
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from copy import deepcopy
# requests uses JSONDecodeError from simplejson if available (ie, atm not on myapp)
try:
    from simplejson.errors import JSONDecodeError
except ImportError:
    from json.decoder import JSONDecodeError


# configure logger
logger = logging.getLogger(__name__)


def get_json_from_portal(issn):

    """Returns a dictionary with the complete JSON data for a given ISSN."""

    # using a requests session to implement a retry strategy. independent of the query
    # interval (0 to 2 seconds) our requests timed out in appr. 1 of 1000 cases.
    session = requests.Session()
    retries = Retry(total=6, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    response = session.get(f'https://portal.issn.org/resource/ISSN/{issn}?format=json')

    # cases we need to handle:
    #     * status code 403: forbidden. this could be a temporary ban when we looked
    #       suspicious somehow. stopping the script is nice behavior. code 429 should be
    #       handled appropriately by urllib3 without our intervention.
    #     * status code 200 / response ok:
    #         - the given ISSN does not exist: no JSON response, redirect to user input
    #           (response history will say 302, page says ISSN not valid)
    #         - successful JSON response, existing ISSN (response history empty)
    #     * other status codes. those should simply get logged.

    # stop here, if we appear to be banned
    if response.status_code == 403:                                 # int, no quotes
        logger.error('Got 403 (forbidden) from ISSN Portal. Stopping query now.')
        return '403 abort now', None

    if response.ok:
        try:                                                        # expected case
            response_as_dict = response.json()
            return response_as_dict, response.text
        except JSONDecodeError:
            if 'The requested numbers do not correspond to valid ISSNs' in response.text:
                return 'invalid ISSN', None
            else:
                return 'JSON decode error', None
    else:
        return str(response.status_code), None


def extract_keepers_from(issn, response_dict):

    """Extracts the Keepers data from the JSON response in its dictionary form."""

    # setting up our output dictionary. more items will get added dynamically.
    # leading numbers are for sorting the columns later.
    keepers_info = {'01 ISSN': issn,
                    '02 ISSN Status': 'n.a.',
                    '03 ISSN Record Status': 'n.a.',
                    '04 ISSN-L': [],                    # likely always one, list for testing
                    '05 ISSN-L Status': 'n.a.',
                    '06 Cancelled in Favor of': [],
                    '07 mainTitle': 'n.a.',
                    '08 keyTitle': 'n.a.',
                    '10 Holding Archives': []}

    # logic switches for ArchiveOrganization node and general checks
    empty_keepers_info = deepcopy(keepers_info)
    keepers_in_json = False
    organizations_in_archivecomponent = set()
    organizations_in_archiveorganization = set()
    org_names = {}

    # warn when record looks a little short for a stormtrooper
    number_of_nodes = len(response_dict['@graph'])
    if number_of_nodes <= 5:
        logger.warning(f'Only {number_of_nodes} nodes in the record. The data is likely incomplete or invalid.' )

    # iterating through the nodes in "@graph", mapping the data we are interested in.
    # the semantics are documented in the "ISSN linked data application profile".
    for element in response_dict['@graph']:
        if '@type' in element:

            # ArchiveOrganization nodes are linked from ArchiveComponent nodes. used only for
            # a simple validity check later, and gathering full organization names.
            if element['@type'] == 'http://schema.org/ArchiveOrganization':
                for key in element.keys():                  # known variants are "identifier"
                    if 'identifier' in key:                 # and "http://schema.org/identifier"
                        organizations_in_archiveorganization.add(element[key])
                        org = element[key].split('#')[-1]
                        if org not in org_names:
                            org_names[org] = set()
                        org_names[org].add(element.get('name', 'no org name found'))
                if 'identifier' not in str(element.keys()):                 # kinda sloppy
                    organizations_in_archiveorganization.add('MISSING')     # but close enough

            # mapping contents of ArchiveComponent nodes
            if element['@type'] == 'http://schema.org/ArchiveComponent':
                # we encountered records reporting an archived range in "description" while
                # the node is missing holdingArchive information. this happens rarely (3 in 10000).
                # since such a node is incomplete, we note it in the log and continue to the
                # next node.
                holding_archive_string = element.get('holdingArchive', 'HOLDING ARCHIVE MISSING')
                if holding_archive_string == 'HOLDING ARCHIVE MISSING':
                    logger.warning('Detected missing "holdingArchive" information in node. '
                                   'Skipping incomplete node.')
                    continue

                # list of all encountered archives
                holding_archive = holding_archive_string.split('#')[-1]
                organizations_in_archivecomponent.add(holding_archive)
                keepers_info['10 Holding Archives'].append(holding_archive)

                # dynamically mapping archival information
                if f'{holding_archive} creativeWorkStatus' not in keepers_info.keys():
                    keepers_info[f'{holding_archive} creativeWorkStatus'] = []
                    keepers_info[f'{holding_archive} description'] = []
                    keepers_info[f'{holding_archive} temporalCoverage'] = []
                status = element['creativeWorkStatus']
                description = element.get('description', 'n.a.')
                if not description.casefold().startswith(status.casefold()):
                    description = f'{status} : {description}'
                temporal_coverage = f'{status} : {element.get("temporalCoverage", "n.a.")}'
                keepers_info[f'{holding_archive} creativeWorkStatus'].append(status)
                keepers_info[f'{holding_archive} description'].append(description)
                keepers_info[f'{holding_archive} temporalCoverage'].append(temporal_coverage)

        if element.get('@id') == f'resource/ISSN/{issn}#ISSN':
            keepers_info['02 ISSN Status'] = element.get('status', 'n.a.').split('#')[-1]
        if element.get('@id') == f'resource/ISSN/{issn}#ISSN-L':
            keepers_info['04 ISSN-L'].append(element.get('value', 'n.a.'))
            keepers_info['05 ISSN-L Status'] = element.get('status', 'n.a.').split('#')[-1]
        if element.get('@id') == f'resource/ISSN/{issn}#Record':
            record_status = element.get('status', 'n.a.').split('#')[-1]
            keepers_info['03 ISSN Record Status'] = record_status
            if record_status.lower() == 'unreported':
                logger.warning('ISSN record status is "unreported": Not yet assigned or reported.')
            elif record_status.lower() == 'suppressed':
                logger.warning('ISSN record status is "suppressed": Periodical was not published.')
            elif record_status.lower() == 'legacy':
                logger.warning('ISSN record status is "legacy": Bibliographic information likely missing.')
            elif record_status.lower() == 'cancelled':
                logger.warning('ISSN record status is "cancelled": This ISSN was cancelled.')
        if element.get('@id') == f'resource/ISSN/{issn}':
            keepers_info['07 mainTitle'] = element.get('mainTitle', 'n.a.')
            if 'hasIncorrectISSN' in element.keys():
                incorrect_issn = element['hasIncorrectISSN']
                logger.info(f'Record reports incorrect ISSN: {incorrect_issn}.')
                if incorrect_issn == issn:
                    # experience suggests incorrect ISSNs do not have a record, so
                    # we do not expect this to get triggered at all.
                    logger.warning('Used ISSN equals reported incorrect ISSN.')
        if element.get('@id') == f'resource/ISSN/{issn}#KeyTitle':
            keepers_info['08 keyTitle'] = element.get('value', 'n.a.')

        if 'cancelledInFavorOf' in element:
            ersatz_issns = []
            if isinstance(element['cancelledInFavorOf'], str):
                ersatz_issns.append(element['cancelledInFavorOf'])
            elif type(element['cancelledInFavorOf']) == list:
                for item in element['cancelledInFavorOf']:
                    ersatz_issns.append(item)
            else:
                logger.warning('Unexpected data type in field "cancelledInFavorOf".')
            for issn_link in ersatz_issns:
                ersatz_issn = issn_link.split('/')[-1]
                logger.warning(f'This ISSN has been cancelled in favor of {ersatz_issn}.')
                keepers_info['06 Cancelled in Favor of'].append(ersatz_issn)

    # the string "keepers" should not be present in the JSON data, if we did not
    # find any archival data. sometimes it will be, but rarely.
    found_keepers_data = False
    if not keepers_info == empty_keepers_info:
        found_keepers_data = True
    if 'keepers' in str(response_dict).casefold():
        keepers_in_json = True
    if not found_keepers_data and keepers_in_json:
        logger.warning('Found string "keepers" in JSON data, but no Keepers data was mapped.')

    # making sure both nodes, ArchiveComponent and ArchiveOrganization were present
    if organizations_in_archivecomponent != organizations_in_archiveorganization:
        logger.warning('Organizations in "ArchiveComponent" do not match those in "ArchiveOrganization".')
        logger.warning('This indicates incomplete data in the JSON record.')

    # transformations: converting lists to strings with unique items
    holding_archives = sorted(set(keepers_info['10 Holding Archives']))
    number_of_archives = len(holding_archives)
    keepers_info['10 Holding Archives'] = holding_archives
    separated_by_bar = ['description', 'temporalCoverage', 'mainTitle', 'keyTitle']
    for item in keepers_info:
        if len(keepers_info[item]) != 0:
            if type(keepers_info[item]) == list:
                if any(word in item for word in separated_by_bar):
                    keepers_info[item] = ' | '.join(keepers_info[item])
                elif 'creativeWorkStatus' in item:
                    keepers_info[item] = ', '.join(sorted(set(keepers_info[item])))
                else:
                    keepers_info[item] = ', '.join(keepers_info[item])
        else:
            keepers_info[item] = 'n.a.'
    keepers_info['09 Number of Archives'] = number_of_archives          # setting this
                                                                        # earlier breaks things
    return keepers_info, org_names
