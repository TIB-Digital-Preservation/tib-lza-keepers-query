
[DE 🇩🇪](README.md)

# TIB LZA Keepers Query

## What does it do?

The Keepers Query script reads public records from the ISSN Portal. It looks for Keepers data within these records and exports the results as a table (CSV).

## Keepers Data and the ISSN Portal

The [Keepers Registry](https://web.archive.org/web/20191128175758/https://thekeepers.org/) has been a project aiming to provide an exchange mechanism for the archival status of scientific journals. Until 2019 it was located at the _EDINA_ (University of Edinburgh). The data and the responsibility was then taken over by the ISSN International Centre in Paris.  
Archiving institutions provide data about the archival status and archived ranges of their journals to the ISSN Centre. The information then becomes a part of the record's external data.  
The structure of the records is explained in the [ISSN Linked Data Application Profile](https://www.issn.org/understanding-the-issn/assignment-rules/issn-linked-data-application-profile/).

## Usage

### Input: a list of ISSNs

Keepers Query is a Python script. It usually gets executed in a Linux shell. The expected input is a simple list of ISSNs. This list needs to be a textfile, containing exactly one ISSN per line.  
There are not many safety measures in place, so it is advisable to make sure the list is okay before starting the query. The usual mistakes are ISSNs ending with a lower case "x" or unwanted duplicates. In a shell those are easy to fix. First convert all "x" to "X":

    $ cat my_issn_list.txt | tr 'x' 'X' > my_issn_list_X.txt

Then sort the result and eliminate the duplicates:

    $ sort -u my_issn_list_X.txt > my_issn_list_sorted_unique.txt

### The script itself

There is an internal help you can see by typing

    $ ./keepers_issn_query.py --help

To initiate a query you need to provide your ISSN list as a named parameter:

    $ ./keepers_issn_query.py --issns my_issn_list_sorted_unique.txt

There are several more parameters:

* `--issns <issn-list>`: The text file containing your ISSNs.
* `--save-records`: If given, the actual JSON records from the query will be saved in a subfolder. This will be one file per ISSN.
* `--ignore <issn-list>`: A text file with ISSNs you want to ignore in this query.
* `--delay <n>`: A time delay that is added after every single ISSN query. Defaults to one second. Accepts a decimal separator. Politeness suggests to not set this to zero.
* `--level <level>`: Set the loglevel for the logfile. Does not affect screen messages. Useful values are "DEBUG", "WARNING", or "ERROR". The default is "INFO".

### Output

The script writes some of its log messages to the standard output (usually the screen). Several files will be written to the working directory (the location the script is called from):


* `<timestamp>_done_issns.txt`: A list of successfully queried ISSNs. If needed, this can be used with the `--ignore` parameter in a second run. May also be used as a makeshift progress meter by counting the number of lines.
* `<timestamp>_keepers_query.log`: Checking the logfile after a query is mandatory. Look for messages of the levels "ERROR" and "WARNING". An error means we did not get any data for the ISSN. Most warnings indicate something suspicious in the record itself (most of the time missing or sparse data).
* `<timestamp>_keepers_query_results.csv`: A CSV table containing the results of the query.
* `<timestamp>_encountered_archives_list.txt`: A list of the encountered archiving organizations. The CSV table only uses abbreviations for clarity. The full names and their abbreviations are listed in this file.

### The Logfile

There will be at least one line per ISSN. If anything noteworthy happens during the query of this ISSN, the following lines will show errors or warnings. "WARNING" means something seems wrong with the data, "ERROR" means we did not get any data.

Some possible messages, and what they mean:

| Level   | Message                            | Meaning                                                                                                              |
|---------|------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| INFO    | Record reports incorrect ISSN <issn> | Associated incorrect ISSN. This can usually be ignored.                                                              |
| WARNING | Used ISSN equals reported incorrect ISSN | This ISSN references itself as an incorrect ISSN.                                                                    |
| WARNING | ISSN record status is "cancelled"  | ISSN is discontinued / has been replaced by another                                                                  |
| WARNING | ISSN record status is "legacy"     | ISSN record is may be incomplete                                                                                     |
| WARNING | ISSN record status is "suppressed" | journal has never been published                                                                                     |
| WARNING | ISSN record status is "unreported" | may be a legitimate ISSN, but has (yet?) to be reported to the ISSN International Centre                             |
| WARNING | Only N nodes in the record        | the JSON-Record is too small to be considered complete                                                               |
| WARNING | Detected missing "holdingArchive" information in node | incomplete Keepers data; archival range given, but no organization                                                   |
| ERROR   | Invalid JSON data. "@graph" node is missing | the JSON record is damaged; may resolve itself a day later                                                           |
| ERROR | ISSN seems to be unknown to the ISSN Portal | unknown ISSN                                                                                                         |
| ERROR | No valid JSON response for unknown reasons | mostly unknown ISSNs as well; query did not result in a JSON file |

## Known Issues

The script retrieves JSON or HTML responses from the ISSN Portal. As every other script using webscraping, it may stop working any time if the expected structures change. Depending on the severity of the changes adapting the script may or may not be feasible.

Given ISSNs are used to construct the direct path to the ISSN record's JSON representation. This is different from a manual search, which still may find something, even if the requested record itself does not exist.

Internally the script does the complete query first, and exports the results to a CSV last. If the script fails before finishing its job the query must be repeated. Expect the script to freeze when your IP address changes.

In normal operation some queries will pause for minutes or time out. Increasing or decreasing the `--delay` parameter seems to have no effect on this. If a timeout occurs, there will be 5 retries before an exception occurs, ungracefully ending the query.

There is no meaningful check or normalization performed on the input data. If a user supplies a wrong textfile, every line will be sent to the portal as part of a constructed URL.

## Prerequisites

Aside from standard Python modules `requests` is used to obtain the data.

The script is known to work on Ubuntu 20.04 and Ubuntu 22.10.

## License

The script is released under the [MIT License](LICENSE).

