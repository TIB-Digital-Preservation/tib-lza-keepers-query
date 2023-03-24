
[EN 🇬🇧](README_en.md)

# TIB LZA Keepers Query

## Was tut es?

Das Keepers Query Skript liest öffentliche Records aus dem ISSN-Portal aus. Diese werden nach Keepers-Informationen durchsucht und die Ergebnisse in eine Tabelle (CSV) exportiert.

## Keepers-Daten und das ISSN-Portal

Die [Keepers Registry](https://web.archive.org/web/20191128175758/https://thekeepers.org/) war ein Projekt zum Austausch des archivarischen Status von wissenschaftlichen Zeitschriften. Es war bis 2019 am _EDINA_ an der Universität Edinburgh angesiedelt und wurde danach vom _ISSN International Centre_ in Paris übernommen.  
Die archivierenden Institutionen melden Daten über den Status und den Umfang der Archivierung ihrer Zeitschriften an das ISSN Center. Dort werden sie als externe Daten in die ISSN-Records eingebunden.  
Die Struktur der Records ist im [ISSN Linked Data Application Profile](https://www.issn.org/understanding-the-issn/assignment-rules/issn-linked-data-application-profile/) beschrieben.

## Benutzung

### Eingabedaten: ISSNs

Keepers Query ist ein Python-Skript, das in einer Linux-Shell ausgeführt wird. Als Input wird eine Liste der abzufragenden ISSNs benötigt. Diese Liste ist eine Textdatei – jede Zeile enthält genau eine ISSN.  
Wir empfehlen, die Liste vorher in Form zu bringen. Beliebte Fehler sind ISSNs, die mit klein geschriebenem "x" enden oder Dubletten. Das lässt sich beheben, indem zuerst alle "x" zu "X" in Großschreibung konvertiert werden.

    $ cat meine_issn_liste.txt | tr 'x' 'X' > meine_issn_liste_X.txt

Dann sortieren und die Dubletten herausfiltern:

    $ sort -u meine_issn_liste_X.txt > meine_issn_liste_sorted_unique.txt

### Das Python-Skript

Die interne Hilfe des Skripts wird mit 

    $ ./keepers_issn_query.py --help

angezeigt.

Um eine Abfrage zu starten, wird die ISSN-Liste als Parameter mitgegeben:

    $ ./keepers_issn_query.py --issns meine_issn_liste_sorted_unique.txt

Die möglichen Parameter sind:

* `--issns <issn-liste>`: Textdei mit abzufragenden ISSNs.
* `--save-records`: Wenn angegeben, werden die abgefragten JSON-Records als Dateien in einen Unterordner geschrieben.
* `--ignore <issn-liste>`: Textdatei mit ISSNs, die bei der Abfrage ignoriert werden sollen.
* `--delay <n>`: Zeitintervall zwischen den Abfragen einzelner ISSNs. Default ist eine Sekunde. Nachkommastellen sind möglich. Sollte aus Höflichkeit nicht auf Null gesetzt werden.
* `--level <level>`: Loglevel für das Logfile, nicht für die Bildschirmausgabe. Sinnvolle Werte sind "DEBUG", "WARNING" oder "ERROR". Default ist "INFO".

### Ausgabe des Skripts

Das Skript schreibt Logmeldungen in den Standard-Output (auf den Bildschirm). Es werden im Working Directory (der Ort, von dem aus das Skript aufgerufen wurde) mehrere Dateien erzeugt:

* `<timestamp>_done_issns.txt`: Alle erfolgreich abgerufenen ISSNs. Kann bei einer zweiten Ausführung als Ignore-List an das Skript übergeben werden. Die Anzahl der Zeilen während der Ausführung kann als Fortschrittsanzeige interpretiert werden.
* `<timestamp>_keepers_query.log`: Das Logfile sollte nach der Ausführung nach "ERROR" und "WARNING" durchsucht werden. Ein "ERROR" bedeutet, dass die ISSN nicht abgefragt werden konnte.
* `<timestamp>_keepers_query_results.csv`: Die Ergebnisse der Abfrage als CSV-Tabelle.
* `<timestamp>_encountered_archives_list.txt`: Archivierende Institutionen werden in der CSV-Tabelle als Abkürzung aufgeführt. Die Bedeutungen der Abkürzungen – die vollen Namen der Institutionen – stehen in dieser Textdatei.

### Das Logfile

Für jede ISSN wird bei Abruf im Log eine Zeile erzeugt. Kommt das danach zu Fehlern, stehen diese in den unmittelbar folgenden Zeilen. Die Fehler werden unterschieden in "WARNING" – Unstimmigkeiten bei den abgerufenen Daten – und "ERROR" – das Abrufen der Daten schlug fehl.

Einige mögliche Fehler:

| Level   | Fehler                             | Bedeutung                                                                        |
|---------|------------------------------------|----------------------------------------------------------------------------------|
| INFO    | Record reports incorrect ISSN <issn> | Nur problematisch, wenn die angeführten ISSNs in der Eingabeliste enthalten sind |
| WARNING | Used ISSN equals reported incorrect ISSN | ISSN bezeichnet sich selbst als falsch                                           |
| WARNING | ISSN record status is "cancelled"  | ISSN wurde eingestellt und durch eine andere ersetzt                             |
| WARNING | ISSN record status is "legacy"     | ISSN-Eintrag möglicherweise unvollständig                                        |
| WARNING | ISSN record status is "suppressed" | Zeitschrift ist nie erschienen                                                   |
| WARNING | ISSN record status is "unreported" | legitime ISSN, aber (noch?) keine Meldung an das ISSN Center erfolgt            |
| WARNING | Only N nodes in the record        | JSON-Record ist eigentlich zu klein, um vollständig zu sein                      |
| WARNING | Detected missing "holdingArchive" information in node | Unvollständige Keepers Daten; Archivierungszeitraum ohne Organisationsname       |
| ERROR   | Invalid JSON data. "@graph" node is missing | Die JSON-Datei war (vorübergehend) kaputt                                        |
| ERROR | ISSN seems to be unknown to the ISSN Portal | unbekannte ISSN |
| ERROR | No valid JSON response for unknown reasons | oft auch unbekannt; Anfrage führte zu keinen Daten |


### Bekannte Probleme

Das Skript nutzt Webscraping, um JSON-Dateien aus dem ISSN-Portal abzurufen. Zusätzlich wertet es ggf. einige HTML-Responses aus. Grundsätzlich kann jedes Webscraping-Skript zu jeder Zeit obsolet werden, wenn die Struktur der abgefragten Daten sich ändert. Das kann bedeuten, dass nach einer Änderung am ISSN-Portal das Skript angepasst werden muss. Im Extremfall ist das nicht möglich und das Skript ist obsolet.

Die ISSNs werden direkt für den Abruf der Daten als JSON-Datei benutzt. Dies unterscheidet sich von einer manuellen Suche im ISSN-Portal. Verbindungen durch Linking ISSNs oder andere Strukturen werden nicht verfolgt.

Das Skript fragt zuerst alle Records ab und generiert die Ergebnistabelle am Ende der Abfrage. Sollte es vorher zu Abstürzen oder Unterbrechungen der Internetverbindung kommen, muss die Abfrage komplett wiederholt werden.

Es ist normal, dass es bei einer größeren Anzahl von ISSNs zwischendurch zu Pausen oder sogar Timeouts kommt. Erfahrungsgemäß hat die Variation des `--delay`-Parameters darauf keinen Einfluss. Bei einem Timeout finden bis zu 5 Retries statt. Danach kommt es zu einer Exception und das Skript bricht ab.

Die Eingabezeilen aus der ISSN-Liste werden nicht strukturell plausibilisert. Bei versehentlicher Angabe einer anderen Textdatei würden die enthaltenen Zeilen als Anfrage an das ISSN-Portal gesendet.

## Technische Voraussetzungen

Neben einigen Standard-Modulen von Python wird `requests` für die Web-Abfragen genutzt.

Erfolgreich getestet wurde das Skript unter Ubuntu 20.04 und Ubuntu 22.10.

## Lizenz

Dieses Skript steht unter der [MIT-Lizenz](LICENSE).



