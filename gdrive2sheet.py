#!/usr/bin/python

import argparse
import sys
import datetime
import logging
import os
from gsheet_wrapper import GSheetWrapper, GSheetOptions
from os.path import expanduser
import datetime
import time
from result_printer import ResultPrinter
from logging.handlers import TimedRotatingFileHandler

from file_utils import FileUtils

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
        ch = logging.StreamHandler()
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

        if args.issues and len(args.issues) > 0:
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



class Gdrive2Sheet:
    def __init__(self, args):
        self.setup_dirs()
        self.operation_mode = args.operation_mode
        if self.operation_mode == OperationMode.GSHEET:
            self.gsheet_wrapper = GSheetWrapper(args.gsheet_options)

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
        self.validate_operation_mode()
        # TODO call list_shared_files here
        self.print_results_table()
        if gdrive2sheet.operation_mode == OperationMode.GSHEET:
            LOG.info("Updating Google sheet with results...")
            self.update_gsheet()

    def print_results_table(self):
        data, headers = self.convert_data_for_result_printer()
        result_printer = ResultPrinter(data, headers)
        result_printer.print_table()

    def update_gsheet(self):
        update_date_str = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        # TODO update gsheet with values here

    def convert_data_for_result_printer(self):
        data = []
        #TODO specify headers here
        headers = []
        #TODO convert data here

        return data, headers


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
