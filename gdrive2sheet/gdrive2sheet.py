#!/usr/bin/python

import argparse
import sys
import datetime as dt
import logging
from enum import Enum
from typing import List, Dict
from pythoncommons.file_utils import FileUtils
from pythoncommons.google.common import ServiceType
from pythoncommons.google.google_auth import GoogleApiAuthorizer
from pythoncommons.google.google_sheet import GSheetOptions, GSheetWrapper
from pythoncommons.google.google_drive import DriveApiWrapper, FileField, DriveApiFile
import time
from logging.handlers import TimedRotatingFileHandler
from pythoncommons.project_utils import ProjectUtils
from pythoncommons.result_printer import BasicResultPrinter

LOG = logging.getLogger(__name__)

__author__ = 'Szilard Nemeth'
PROJECT_NAME = "gdrive2sheet"


class OperationMode(Enum):
    GSHEET = "GSHEET"
    PRINT = "PRINT"


class Setup:
    @staticmethod
    def init_logger(log_dir, console_debug=False, postfix=""):
        # get root logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        # create file handler which logs even debug messages
        log_file = FileUtils.join_path(log_dir, ProjectUtils.get_default_log_file(PROJECT_NAME, postfix=postfix))
        fh = TimedRotatingFileHandler(log_file, when="midnight")
        fh.suffix = "%Y_%m_%d.log"
        fh.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(logging.INFO)
        if console_debug:
            ch.setLevel(logging.DEBUG)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
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
            print(f"Using operation mode: {OperationMode.PRINT.value}")
            args.operation_mode = OperationMode.PRINT
        elif args.gsheet:
            print(f"Using operation mode: {OperationMode.GSHEET.value}")
            args.operation_mode = OperationMode.GSHEET
            args.gsheet_options = GSheetOptions(args.gsheet_client_secret,
                                                args.gsheet_spreadsheet,
                                                args.gsheet_worksheet)
        else:
            print("Unknown operation mode!")

        return args


# TODO move to python-commons
class RowStats:
    def __init__(self, list_of_fields: List[str], track_unique: List[str] = None):
        self.list_of_fields = list_of_fields
        self.track_unique_values = track_unique
        if not self.track_unique_values:
            self.track_unique_values = []

        self.longest_fields: Dict[str, str] = {field: "" for field in list_of_fields}
        self.unique_values: Dict[str, set] = {}
        self.longest_line = ""

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

        self.authorizer = GoogleApiAuthorizer(ServiceType.DRIVE)
        self.drive_wrapper = DriveApiWrapper(self.authorizer)
        self.headers = FileField.PRINTABLE_FIELD_DISPLAY_NAMES
        self.file_fields = FileField.GOOGLE_API_FIELDS_COMMA_SEPARATED
        self.data = None

    def validate_operation_mode(self):
        if self.operation_mode == OperationMode.PRINT:
            LOG.info("Using operation mode: %s", OperationMode.PRINT)
        elif self.operation_mode == OperationMode.GSHEET:
            LOG.info("Using operation mode: %s", OperationMode.GSHEET)
        else:
            raise ValueError("Unknown state! Operation mode should be either "
                             "{} or {} but it is {}"
                             .format(OperationMode.PRINT,
                                     OperationMode.GSHEET,
                                     self.operation_mode))

    def setup_dirs(self):
        ProjectUtils.get_output_basedir(PROJECT_NAME)
        ProjectUtils.get_logs_dir()

    @property
    def get_logs_dir(self):
        return ProjectUtils.get_logs_dir()

    def sync(self):
        drive_api_file_list: List[DriveApiFile] = self.drive_wrapper.get_shared_files(fields=self.file_fields)
        # TODO debug log raw data here
        truncate = gdrive2sheet.operation_mode == OperationMode.PRINT
        self.data: List[List[str]] = DataConverter.convert_data_to_rows(drive_api_file_list, truncate=truncate)

        self.print_results_table()
        if gdrive2sheet.operation_mode == OperationMode.GSHEET:
            LOG.info("Updating Google sheet with data...")
            self.update_gsheet()

    def print_results_table(self):
        if not self.data:
            raise ValueError("Data is not yet set, please call sync method first!")
        BasicResultPrinter.print_table(self.data, self.headers)

    def update_gsheet(self):
        if not self.data:
            raise ValueError("Data is not yet set, please call sync method first!")
        self.gsheet_wrapper.write_data(self.headers, self.data)


class DataConverter:
    TITLE_MAX_LENGTH = 50
    LINK_MAX_LENGTH = 20

    @staticmethod
    def convert_data_to_rows(drive_api_file_list, truncate: bool = False) -> List[List[str]]:
        converted_data: List[List[str]] = []
        truncate_titles: bool = truncate
        truncate_links: bool = truncate
        truncate_dates: bool = truncate

        row_stats: RowStats = RowStats(["name", "link", "date", "owners", "type"], track_unique=["type"])
        for api_file in drive_api_file_list:
            name = str(api_file.name)
            link = str(api_file.link)
            date = str(api_file.shared_with_me_date)
            owners = ",".join([o.name for o in api_file.owners])
            mimetype = DriveApiWrapper.convert_mime_type(str(api_file.mime_type))
            row_stats.update({"name": name, "link": link, "date": date, "owners": owners, "type": mimetype})

            if truncate_titles and len(name) > DataConverter.TITLE_MAX_LENGTH:
                name = DataConverter._truncate_str(name, DataConverter.TITLE_MAX_LENGTH, "title")
            if truncate_links:
                link = DataConverter._truncate_str(link, DataConverter.LINK_MAX_LENGTH, "link")
            if truncate_dates:
                date = DataConverter._truncate_date(date)

            row: List[str] = [name, link, date, owners, mimetype]
            converted_data.append(row)
        row_stats.print_stats()
        return converted_data

    @staticmethod
    def _truncate_str(value, max_len, field_name):
        orig_value = value
        truncated = value[0:max_len] + "..."
        LOG.debug(f"Truncated {field_name}: "
                  f"Original value: '{orig_value}', "
                  f"Original length: {len(orig_value)}, "
                  f"New value (truncated): {truncated}, "
                  f"New length: {max_len}")
        return truncated

    @staticmethod
    def _truncate_date(date):
        original_date = date
        date_obj = dt.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ')
        truncated = date_obj.strftime("%Y-%m-%d")
        LOG.debug(f"Truncated date. "
                  f"Original value: {original_date},"
                  f"New value (truncated): {truncated}")
        return truncated


if __name__ == '__main__':
    start_time = time.time()

    # Parse args
    args = Setup.parse_args()
    gdrive2sheet = Gdrive2Sheet(args)

    # Initialize logging
    verbose = True if args.verbose else False
    Setup.init_logger(gdrive2sheet.get_logs_dir, console_debug=verbose)

    gdrive2sheet.sync()
    end_time = time.time()
    LOG.info("Execution of script took %d seconds", end_time - start_time)
