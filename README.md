# GDrive2sheet

This project is able to sync Google drive documents (along with their metadata) to a Google sheet.

### Getting started / Setup

You need to have python 2.7 and pip installed.
Run make from the project's root directory, all python dependencies required by the project will be installed.


## Running the tests

TODO

## Main dependencies

* [gspread](https://gspread.readthedocs.io/en/latest/) - gspread is a Python API for Google Sheets
* [tabulate](https://pypi.org/project/tabulate/) - python-tabulate: Pretty-print tabular data in Python, a library and a command-line utility.
* [oauth2client](https://oauth2client.readthedocs.io/en/latest/) - oauth2client: Used to authenticate with Google Sheets

## Contributing

TODO 

## Authors

* **Szilard Nemeth** - *Initial work* - [Szilard Nemeth](https://github.com/szilard-nemeth)

## License

TODO 

## Acknowledgments

TODO

## Example commands

1. Print names of Google drive documents
```python ./gdrive2sheet.py --print```

2. Sync Google Drive documents and their metadata to a Google Sheet.

If --gsheet is specified, a number of other Google Sheet specific arguments are required: 
  * --gsheet-client-secret: File to be used for authenticate to Google Sheets API.
  * --gsheet-spreadsheet: Name of the spreadsheet (document) on Google Sheet.
  * --gsheet-worksheet: The name of the worksheet from the spreadsheet (document).
  
```
python ./gdrive2sheet/gdrive2sheet.py --gsheet -v \
--gsheet-client-secret "/Users/szilardnemeth/.secret/client_secret_hadoopreviewsync.json" \ 
--gsheet-spreadsheet "Documents shared with me in Google Drive"
--gsheet-worksheet "Sheet1"
```