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
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

CREDENTIALS_FILENAME = 'credentials.json'
TOKEN_FILENAME = 'token.pickle'

PORT = 49555
ORDER_BY = "sharedWithMeTime desc"
PAGESIZE = 100
QUERY = "sharedWithMe"
ALL_FIELDS_WITH_DISPLAY_NAME = [("id", "ID"), ("name", "Name"), ("mimeType", "Type"), ("webViewLink", "Link"),
                                ("createdTime", "Created date"), ("modifiedTime", "Last modified time"),
                                ("sharedWithMeTime", "Shared with me date"),
                                ("sharingUser", "Sharing user"), ("owners", "Owner")]
GOOGLE_API_FIELDS = [tup[0] for tup in ALL_FIELDS_WITH_DISPLAY_NAME]
FIELD_DISPLAY_NAMES = [tup[1] for tup in ALL_FIELDS_WITH_DISPLAY_NAME]
# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']


def main():
    """
    """
    creds = authorize()

    service = build('drive', 'v3', credentials=creds)
    files_service = service.files()

    fields = get_field_names()
    list_files_with_paging(files_service, QUERY, PAGESIZE, fields, ORDER_BY)


def get_field_names():
    # File fields are documented here: https://developers.google.com/drive/api/v3/reference/files#resource
    fields_str = ", ".join(GOOGLE_API_FIELDS)
    file_fields = "files(" + fields_str + ")"
    fields = "nextPageToken, " + file_fields
    return fields


def authorize():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_FILENAME):
        with open(TOKEN_FILENAME, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILENAME, SCOPES)
            creds = flow.run_local_server(port=PORT)
        # Save the credentials for the next run
        with open(TOKEN_FILENAME, 'wb') as token:
            pickle.dump(creds, token)
    return creds


def list_files_with_paging(files, query, page_size, fields, order_by):
    request = files.list(q=query, pageSize=page_size, fields=fields, orderBy=order_by)
    while request is not None:
        files_doc = request.execute()
        print_files(files_doc)
        request = files.list_next(request, files_doc)


def print_files(results):
    if not results:
        print('No files found.')
    else:
        items = results.get('files', [])
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['sharedWithMeTime']))


if __name__ == '__main__':
    main()
