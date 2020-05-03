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
FIELDS = ["id", "name", "mimeType", "webViewLink", "createdTime", "modifiedTime", "sharedWithMeTime", "sharingUser", "owners"]
# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']


def main():
    """
    """
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

    service = build('drive', 'v3', credentials=creds)

    files = service.files()
    # File fields are documented here: https://developers.google.com/drive/api/v3/reference/files#resource
    fields_str = ", ".join(FIELDS)
    file_fields = "files(" + fields_str + ")"
    fields = "nextPageToken, " + file_fields
    request = files.list(q=QUERY, pageSize=PAGESIZE, fields=fields, orderBy=ORDER_BY)
    while request is not None:
        files_doc = request.execute()
        list_files(files_doc)
        request = files.list_next(request, files_doc)


def list_files(results):
    if not results:
        print('No files found.')
    else:
        items = results.get('files', [])
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['sharedWithMeTime']))


if __name__ == '__main__':
    main()
