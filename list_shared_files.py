# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START drive_quickstart]
from __future__ import print_function

from gdrive2sheet.drive_api import DriveApiWrapper


def main():
    """
    """
    drive_wrapper = DriveApiWrapper()
    #drive_wrapper.print_shared_files()

    # files = drive_wrapper.get_shared_files(fields=DriveApiFileFields.GOOGLE_API_FIELDS_COMMA_SEPARATED)
    # print(files)


if __name__ == '__main__':
    main()
