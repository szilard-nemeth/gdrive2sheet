import gspread
import logging

from gspread import SpreadsheetNotFound, WorksheetNotFound
from oauth2client.service_account import ServiceAccountCredentials

SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
LOG = logging.getLogger(__name__)


class GSheetOptions:
    def __init__(self, client_secret, spreadsheet, worksheet):
        self.client_secret = client_secret
        self.spreadsheet = spreadsheet
        self.worksheet = worksheet

    def __repr__(self):
        return repr((self.client_secret, self.spreadsheet, self.worksheet))

    def __str__(self):
        return self.__class__.__name__ + \
               " { " \
               "spreadsheet: " + self.spreadsheet + \
               ", worksheet: " + str(self.worksheet) + " }"


class GSheetWrapper:
    def __init__(self, options):
        if not isinstance(options, GSheetOptions):
            raise ValueError('options must be an instance of GSheetOptions!')

        LOG.debug("GSheetWrapper options: %s", str(options))
        self.options = options

        if not options.client_secret:
            raise ValueError("Client secret should be specified!")

        self.creds = ServiceAccountCredentials.from_json_keyfile_name(options.client_secret, SCOPE)
        self.client = gspread.authorize(self.creds)

    def write_data(self, header, data):
        try:
            sheet = self.client.open(self.options.spreadsheet)
            worksheet = sheet.worksheet(self.options.worksheet)
        except SpreadsheetNotFound:
            raise ValueError("Spreadsheet was not found with name '{}'".format(self.options.spreadsheet))
        except WorksheetNotFound:
            raise ValueError("Worksheet was not found with name '{}'".format(self.options.worksheet))

        all_values = [header]
        all_values.extend(data)
        sheet.values_update(
            'Sheet1!A1',
            params={'valueInputOption': 'RAW'},
            body={'values': all_values}
        )

        # for d in data:
        #     sheet.append_row(d)
