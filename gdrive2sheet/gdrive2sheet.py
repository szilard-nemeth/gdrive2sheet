#!/usr/bin/python

import argparse
import sys
import datetime as dt
import logging
import os

from drive_api import DriveApiWrapper, DriveApiFileFields, DriveApiMimeTypes
from gsheet_wrapper import GSheetWrapper, GSheetOptions
from os.path import expanduser
import datetime
import time
from logging.handlers import TimedRotatingFileHandler

from utils import FileUtils, ResultPrinter

LOG = logging.getLogger(__name__)

__author__ = 'Szilard Nemeth'

class OperationMode:
  GSHEET = "GSHEET"
  PRINT = "PRINT"


class Setup:
    @staticmethod
    def init_logger(log_dir, console_debug=False):
        # get root logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # create file handler which logs even debug messages
        logfilename = datetime.datetime.now().strftime(
            'gdrive2sheet-%Y_%m_%d_%H%M%S.log')

        fh = TimedRotatingFileHandler(os.path.join(log_dir, logfilename), when='midnight')
        fh.suffix = '%Y_%m_%d.log'
        fh.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(logging.INFO)
        if console_debug:
            ch.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        # add the handlers to the logger
        logger.addHandler(fh)
        logger.addHandler(ch)

    @staticmethod
    def parse_args():
        """This function parses and return arguments passed in"""

        parser = argparse.ArgumentParser()

        parser.add_argument('-v', '--verbose', action='store_true',
                            dest='verbose', default=None, required=False,
                            help='More verbose log')

        exclusive_group = parser.add_mutually_exclusive_group(required=True)
        exclusive_group.add_argument('-p', '--print', nargs='+', type=str, dest='do_print',
                                     help='Print results to console',
                                     required=False)
        exclusive_group.add_argument('-g', '--gsheet', action='store_true',
                                     dest='gsheet', default=False,
                                     required=False,
                                     help='Export values to Google sheet. '
                                          'Additional gsheet arguments need to be specified!')

        # Arguments for Google sheet integration
        gsheet_group = parser.add_argument_group('google-sheet', "Arguments for Google sheet integration")

        gsheet_group.add_argument('--gsheet-client-secret',
                                  dest='gsheet_client_secret', required=False,
                                  help='Client credentials for accessing Google Sheet API')

        gsheet_group.add_argument('--gsheet-spreadsheet',
                                  dest='gsheet_spreadsheet', required=False,
                                  help='Name of the GSheet spreadsheet')

        gsheet_group.add_argument('--gsheet-worksheet',
                                  dest='gsheet_worksheet', required=False,
                                  help='Name of the worksheet in the GSheet spreadsheet')

        args = parser.parse_args()
        print("Args: " + str(args))

        # TODO check existence + readability of secret file!!
        if args.gsheet and (args.gsheet_client_secret is None or
                            args.gsheet_spreadsheet is None or
                            args.gsheet_worksheet is None):
            parser.error("--gsheet requires --gsheet-client-secret, --gsheet-spreadsheet and --gsheet-worksheet.")

        if args.do_print:
            print("Using operation mode: print")
            args.operation_mode = OperationMode.PRINT
        elif args.gsheet:
            print("Using operation mode: gsheet")
            args.operation_mode = OperationMode.GSHEET
            args.gsheet_options = GSheetOptions(args.gsheet_client_secret,
                                                args.gsheet_spreadsheet,
                                                args.gsheet_worksheet)
        else:
            print("Unknown operation mode!")

        return args


class RowStats:
    def __init__(self, list_of_fields, track_unique=None):
        self.list_of_fields = list_of_fields
        self.longest_fields = {}
        self.unique_values = {}
        for f in list_of_fields:
            self.longest_fields[f] = ""
        self.longest_line = ""

        self.track_unique_values = track_unique
        if not self.track_unique_values:
            self.track_unique_values = []

    def update(self, row_dict):
        # Update longest fields dict values if required
        for field_name in self.list_of_fields:
            self._update_field(field_name, row_dict[field_name])

        for field_name in self.track_unique_values:
            if field_name not in self.unique_values:
                self.unique_values[field_name] = set()
            self.unique_values[field_name].add(row_dict[field_name])

        # Store longest line
        sum_length = 0
        for field_name in self.list_of_fields:
            sum_length += len(row_dict[field_name])
        if sum_length > len(self.longest_line):
            self.longest_line = ",".join(row_dict.values())

    def _update_field(self, field_name, field_value):
        if len(field_value) > len(self.longest_fields[field_name]):
            self.longest_fields[field_name] = field_value

    def print_stats(self):
        LOG.info("Longest line is: '%s' (%d characters)", self.longest_line, len(self.longest_line))
        for field_name in self.track_unique_values:
            self._print(field_name)

        if len(self.unique_values) > 0:
            for field_name, values_set in self.unique_values.items():
                LOG.info("Unique values of field '%s': %s", field_name, ",".join(values_set))

    def _print(self, field_name):
        field_value = self.longest_fields[field_name]
        LOG.info("Longest %s is: '%s' (length: %d characters)", field_name, field_value, len(field_value))


class Gdrive2Sheet:
    def __init__(self, args):
        self.setup_dirs()
        self.operation_mode = args.operation_mode
        self.validate_operation_mode()

        if self.operation_mode == OperationMode.GSHEET:
            self.gsheet_wrapper = GSheetWrapper(args.gsheet_options)

        self.drive_wrapper = DriveApiWrapper()
        self.headers = DriveApiFileFields.PRINTABLE_FIELD_DISPLAY_NAMES
        self.file_fields = DriveApiFileFields.GOOGLE_API_FIELDS_COMMA_SEPARATED
        self.data = None

    def validate_operation_mode(self):
        if self.operation_mode == OperationMode.PRINT:
            LOG.info("Using operation mode: %s", OperationMode.PRINT)
        elif self.operation_mode == OperationMode.GSHEET:
            LOG.info("Using operation mode: %s", OperationMode.GSHEET)
        else:
            raise ValueError("Unknown state! Jira fetch mode should be either "
                             "{} or {} but it is {}"
                             .format(OperationMode.PRINT,
                                     OperationMode.GSHEET,
                                     self.operation_mode))

    def setup_dirs(self):
        home = expanduser("~")
        self.project_out_root = os.path.join(home, "gdrive2sheet")
        self.log_dir = os.path.join(self.project_out_root, 'logs')
        FileUtils.ensure_dir_created(self.project_out_root)
        FileUtils.ensure_dir_created(self.log_dir)

    def sync(self):
        raw_data_from_api = self.drive_wrapper.get_shared_files(fields=self.file_fields)
        # TODO debug log raw data here
        truncate = gdrive2sheet.operation_mode == OperationMode.PRINT
        self.data = self.convert_data_to_rows(raw_data_from_api, truncate=truncate)

        self.print_results_table()
        if gdrive2sheet.operation_mode == OperationMode.GSHEET:
            LOG.info("Updating Google sheet with data...")
            self.update_gsheet()

    def print_results_table(self):
        if not self.data:
            raise ValueError("Data is not yet set, please call sync method first!")
        result_printer = ResultPrinter(self.data, self.headers)
        result_printer.print_table()

    def update_gsheet(self):
        if not self.data:
            raise ValueError("Data is not yet set, please call sync method first!")
        self.gsheet_wrapper.write_data(self.headers, self.data)

    def convert_data_to_rows(self, data, truncate=False):
        TITLE_MAX_LENGTH = 50
        LINK_MAX_LENGTH = 20
        converted_data = []
        truncate_links = truncate
        truncate_titles = truncate
        truncate_dates = truncate

        row_stats = RowStats(["name", "link", "date", "owners", "type"], track_unique=["type"])
        for f in data:
            name = str(f.name)
            link = str(f.link)
            date = str(f.shared_with_me_date)
            owners = ",".join([o.name for o in f.owners])
            mimetype = self._convert_mime_type(str(f.mime_type))

            row_stats.update({"name": name, "link": link, "date": date, "owners": owners, "type": mimetype})

            if truncate_titles and len(name) > TITLE_MAX_LENGTH:
                original_name = name
                name = name[0:TITLE_MAX_LENGTH] + "..."
                LOG.debug("Truncated title: '%s', original length: %d, new length: %d",
                          original_name, len(original_name), TITLE_MAX_LENGTH)

            if truncate_links:
                original_link = link
                link = link[0:LINK_MAX_LENGTH]
                LOG.debug("Truncated link: '%s', original length: %d, new length: %d",
                          original_link, len(original_link), LINK_MAX_LENGTH)

            if truncate_dates:
                original_date = date
                date_obj = dt.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ')
                date = date_obj.strftime("%Y-%m-%d")
                LOG.debug("Truncated date: '%s', original value: %s, new value: %s",
                          original_date, original_date, date)

            row = [name, link, date, owners, mimetype]
            converted_data.append(row)
        row_stats.print_stats()
        return converted_data

    def _convert_mime_type(self, mime_type):
        if mime_type in DriveApiMimeTypes.MAPPINGS:
            return DriveApiMimeTypes.MAPPINGS[mime_type]
        else:
            LOG.warning("MIME type not found among possible values: %s. Using MIME type value as is", mime_type)
            return mime_type


if __name__ == '__main__':
    start_time = time.time()

    # Parse args
    args = Setup.parse_args()
    gdrive2sheet = Gdrive2Sheet(args)

    # Initialize logging
    verbose = True if args.verbose else False
    Setup.init_logger(gdrive2sheet.log_dir, console_debug=verbose)

    gdrive2sheet.sync()
    end_time = time.time()
    LOG.info("Execution of script took %d seconds", end_time - start_time)
