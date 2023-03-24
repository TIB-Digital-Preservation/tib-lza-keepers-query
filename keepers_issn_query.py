#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Author: Peter Eisner, Technische Informationsbibliothek (TIB)

# This script iterates over a list of ISSNs, retrieving linked data from
# the ISSN Portal. Information concerning the archival status according
# to Keepers is extracted and saved into a CSV file.

import logging
import argparse
import datetime
import os
from time import sleep
import csv

from keepers_query_func import *


# SETUP

# parse commandline arguments
parser = argparse.ArgumentParser(description='Retrieves Keepers data from the ISSN Portal according'
                                             ' to a given list of ISSNs (textfile). The CSV output '
                                             'is written to the current working directory.')
parser.add_argument('--issns',
                    type=str,
                    required=True,
                    metavar='ISSNs',
                    help='A textfile containing one ISSN per line. Required.')
parser.add_argument('--save-records',
                    action='store_true',
                    default=False,
                    help='Save the JSON records to a folder (named "<timestamp>_json_records").')
parser.add_argument('--ignore',
                    type=str,
                    metavar='IGNORE',
                    help='A textfile containing ISSNs to ignore. Used to skip already done ISSNs.')
parser.add_argument('--delay',
                    type=float,
                    default=1,
                    metavar='DELAY',
                    help='Pause politely between queries in seconds. Default 1 second.')
parser.add_argument('--level',
                    type=str,
                    default='INFO',
                    metavar='LOGLEVEL',
                    help='Set the loglevel for the logfile. (DEBUG, INFO, ERROR)')
cl_args = parser.parse_args()
issn_list = cl_args.issns
ignore_list = cl_args.ignore
delay = cl_args.delay
loglevel = cl_args.level.upper()
save_records = cl_args.save_records                            # argparse translates "-" --> "_"

# human-readable timestamp used in output file names
now = datetime.datetime.today()
timestamp = now.strftime('%Y-%m-%d_%H-%M-%S')

# output files
output_csv = f'{timestamp}_keepers_query_results.csv'
organizations_list = f'{timestamp}_encountered_archives_list.txt'
done_issns = f'{timestamp}_done_issns.txt'
logfile = f'{timestamp}_keepers_query.log'
if save_records:
    json_folder = f'{timestamp}_json_records'
    os.mkdir(json_folder)

# set up logging -- "file" to logfile, "stream" to screen (stdout)
logger = logging.getLogger()             # using root logger
logger.setLevel(loglevel)
formatter_file = logging.Formatter('%(asctime)s   %(levelname)-8s   %(message)s   (%(name)s)')
formatter_stream = logging.Formatter('%(levelname)-8s   %(message)s')
file_handler = logging.FileHandler(logfile)
file_handler.setFormatter(formatter_file)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_stream)
stream_handler.setLevel(logging.INFO)    # hardcoded on stdout
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

logger.info(f'Using ISSN list: {issn_list}')
if ignore_list:
    logger.info(f'Ignoring ISSN from file:  {ignore_list}')
if save_records:
    logger.info(f'JSON records will be saved to {json_folder}')
logger.info(f'Delay between queries: {delay} seconds.')

# results go into a list of dictionaries. after the per ISSN loop is done, the
# gathered data will be written to a CSV file. downsides: it's all in memory and
# in case of a crash we loose data. upside: generating the CSV becomes easier
# when we know all the dynamically generated keys.
accumulated_results = []


# MAIN SCRIPT

# make ISSN list
issns = []
with open(issn_list, 'r') as issnfile:
    logger.info('Reading ISSN list.')
    for line in issnfile:
        issns.append(line.rstrip())         # removing newlines

# this removes all ISSNs given in the ignore list. the while loop ensures all
# occurrences of a given ISSN are removed.
if ignore_list:
    logger.info('Removing ignored ISSNs from list. (May take a while.)')
    with open(ignore_list, 'r') as ignorelist:
        for line in ignorelist:
            ignored_issn = line.rstrip()
            while ignored_issn in issns:                       # by itself 'remove' stops
                issns.remove(ignored_issn)                     # after first occurrence

# making sure ISSNs do not end with lowercase x.
for position in range(len(issns)):
    if issns[position].endswith('x'):
        logger.debug(f'Found input ISSN ending with lower x: {issns[position]}')
        issns[position] = issns[position].upper()

# we are collecting relations between shorthands for archive organizations and
# their full names as reported in ArchiveOrganization nodes. representing this
# as a dict {"shorthand": {"org name var a", "org name var b"}} in case there are
# variants in full names.
organization_names = {}


# per ISSN loop
for issn in issns:

    logger.info(f'### Working on ISSN {issn}.')

    json_data, json_text = get_json_from_portal(issn)

    if type(json_data) is not dict:                    # meaning we did not get what we came for
        if json_data == '403 abort now':
            logger.error('Got 403 (forbidden) from ISSN Portal. Stopping query now.')
            import sys
            sys.exit(1)
        else:
            if json_data == 'invalid ISSN':
                logger.error('ISSN seems to be unknown to the ISSN Portal.')
            elif json_data == 'JSON decode error':
                logger.error('No valid JSON response for unknown reasons.')
            else:
                logger.error(f'Received HTTP status {json_data} from ISSN Portal. No data.')
            logger.info('Continuing with next ISSN.')
            continue
    else:                                              # meaning we have a JSON response
        if '@graph' in json_data:
            keepers_data, org_names = extract_keepers_from(issn, json_data)
        else:
            logger.error('Invalid JSON data. "@graph" node is missing.')
            logger.info('Continuing with next ISSN.')
            continue

    # append results
    accumulated_results.append(keepers_data)
    for item in org_names:
        if item not in organization_names:
            organization_names[item] = set()
        organization_names[item] = organization_names[item].union(org_names[item])

    # append done_issns file
    with open(done_issns, 'a') as doneissns:
        doneissns.write(f'{issn}\n')

    # save the json record
    if save_records:
        with open(os.path.join(json_folder, f'{issn}.json'), 'w') as jsonfile:
            jsonfile.writelines(json_text)

    # wait politely
    logger.debug(f'Waiting {delay} seconds...')
    sleep(delay)

# write results to CSV
all_items_occured = set()
for result in accumulated_results:
    all_items_occured.update(result)
header = sorted(list(all_items_occured))

with open(output_csv, 'w') as csvfile:
    logger.info(f'Writing results to file {output_csv}.')
    writer = csv.writer(csvfile)
    writer.writerow(header)
    for item in accumulated_results:
        writer.writerow([item.get(i, 'n.a.') for i in header])

# write list of organizations
with open(organizations_list, 'w') as orglist:
    orglist.write(f'List of Archive Organizations in Query\nstarted at {timestamp}\n\n')
    for item in organization_names:
        orglist.write(f'{item.ljust(20)} {" | ".join(organization_names[item])}\n')
    orglist.write('\n')

logger.info('Query completed.')
logger.info(f'Feel free to check the logfile ({logfile}) for errors or warnings.')
logger.info('Done.')
