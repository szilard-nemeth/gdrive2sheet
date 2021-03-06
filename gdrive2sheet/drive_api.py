import logging
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pythoncommons.string_utils import StringUtils, auto_str

LOG = logging.getLogger(__name__)


class DriveApiMimeTypes:
    #https://stackoverflow.com/questions/4212861/what-is-a-correct-mime-type-for-docx-pptx-etc
    #https://stackoverflow.com/questions/11894772/google-drive-mime-types-listing
    MAPPINGS = {
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "MS Presentation (pptx)",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "MS Word document (docx)",
        "application/vnd.ms-powerpoint": "MS Presentation (ppt)",

        "application/pdf": "PDF document",
        "application/x-apple-diskimage": "Apple disk image",
        "application/zip": "Zip file",
        "text/plain": "Plain text file",
        "application/msword": "MS Word document (doc)",
        
        "image/jpeg": "JPEG image",
        "image/gif": "GIF image",
        "video/mp4": "Video (mp4)",

        "application/vnd.google-apps.spreadsheet": "Google sheet",
        "application/vnd.google-apps.folder": "Google drive folder",
        "application/vnd.google-apps.document": "Google doc",
        "application/vnd.google-apps.form": "Google form",
        "application/vnd.google-apps.presentation": "Google presentation",
        "application/vnd.google-apps.map": "Google map",
    }

class DriveApiFileFields:
    F_OWNER = "owners"
    SHARING_USER = "sharingUser"
    SHARED_WITH_ME_TIME = "sharedWithMeTime"
    MODIFIED_TIME = "modifiedTime"
    CREATED_TIME = "createdTime"
    LINK = "webViewLink"
    MIMETYPE = "mimeType"
    NAME = "name"
    ID = "id"

    _ALL_FIELDS_WITH_DISPLAY_NAME = [(ID, "ID"), (NAME, "Name"), (MIMETYPE, "Type"), (LINK, "Link"),
                                     (CREATED_TIME, "Created date"), (MODIFIED_TIME, "Last modified time"),
                                     (SHARED_WITH_ME_TIME, "Shared with me date"), (F_OWNER, "Owner")]

    PRINTABLE_FIELD_DISPLAY_NAMES = ["Name", "Link", "Shared with me date", "Owner", "Type"]
    # FIELDS_TO_PRINT = [tup[0] for tup in FIELDS_TO_PRINT]

    BASIC_FIELDS_COMMA_SEPARATED = ", ".join([ID, NAME])
    GOOGLE_API_FIELDS = [tup[0] for tup in _ALL_FIELDS_WITH_DISPLAY_NAME]
    GOOGLE_API_FIELDS_COMMA_SEPARATED = ", ".join(GOOGLE_API_FIELDS)
    FIELD_DISPLAY_NAMES = [tup[1] for tup in _ALL_FIELDS_WITH_DISPLAY_NAME]


class DriveApiUserFields:
    UNKNOWN_USER = 'unknown'
    EMAIL_ADDRESS = 'emailAddress'
    DISPLAY_NAME = 'displayName'


class DriveApiGenericFields:
    PAGING_NEXT_PAGE_TOKEN = "nextPageToken"


@auto_str
class DriveApiFile(dict):
    def __init__(self, id, name, link, created_date, modified_date, shared_with_me_date, mime_type, owners,
                 sharing_user):
        super(DriveApiFile, self).__init__()
        self.id = id
        self.name = StringUtils.replace_special_chars(name)
        self.link = link
        self.created_date = created_date
        self.modified_date = modified_date
        self.shared_with_me_date = shared_with_me_date
        self.mime_type = mime_type
        self.owners = owners
        self.sharing_user = StringUtils.replace_special_chars(sharing_user)

    def __repr__(self):
        return self.__str__()


@auto_str
class DriveApiUser(dict):
    def __init__(self, owner_dict):
        super(DriveApiUser, self).__init__()
        email = owner_dict[DriveApiUserFields.EMAIL_ADDRESS] if DriveApiUserFields.EMAIL_ADDRESS in owner_dict \
            else DriveApiUserFields.UNKNOWN_USER
        name = owner_dict[DriveApiUserFields.DISPLAY_NAME] if DriveApiUserFields.DISPLAY_NAME in owner_dict \
            else DriveApiUserFields.UNKNOWN_USER
        self.email = email
        self.name = StringUtils.replace_special_chars(name)

    def __repr__(self):
        return self.__str__()


class DriveApiWrapper:
    API_VERSION = 'v3'
    DRIVE_SERVICE = 'drive'
    ORDER_BY_DEFAULT = "sharedWithMeTime desc"
    Q_SHARED_WITH_ME = "sharedWithMe"

    def __init__(self):
        self.authorizer = DriveAuthorizer()
        self.creds = self.authorizer.authorize()

    def print_shared_files(self, page_size=100, fields=None, order_by=ORDER_BY_DEFAULT):
        files = self.get_shared_files(page_size=page_size, fields=fields, order_by=order_by)
        self.print_files(files)

    def get_shared_files(self, page_size=100, fields=None, order_by=None):
        if not fields:
            fields = DriveApiFileFields.BASIC_FIELDS_COMMA_SEPARATED
        if not order_by:
            order_by = self.ORDER_BY_DEFAULT

        service = build(self.DRIVE_SERVICE, self.API_VERSION, credentials=self.creds)
        files_service = service.files()

        fields_str = self.get_field_names_with_pagination(fields)
        return self.list_files_with_paging(files_service, self.Q_SHARED_WITH_ME, page_size, fields_str, order_by)

    @staticmethod
    def get_field_names_with_pagination(fields, resource_type='files'):
        # File fields are documented here: https://developers.google.com/drive/api/v3/reference/files#resource
        fields_str = "{res}({fields})".format(res=resource_type, fields=fields)
        return "{}, {}".format(DriveApiGenericFields.PAGING_NEXT_PAGE_TOKEN, fields_str)

    @staticmethod
    def list_files_with_paging(files_service, query, page_size, fields, order_by):
        result_files = []
        request = files_service.list(q=query, pageSize=page_size, fields=fields, orderBy=order_by)
        while request is not None:
            files_doc = request.execute()
            if files_doc:
                items = files_doc.get('files', [])
                items = [DriveApiWrapper._convert_to_drive_file_object(i) for i in items]
                result_files.extend(items)
            else:
                LOG.warning('No files found.')
            request = files_service.list_next(request, files_doc)

        return result_files

    @classmethod
    def _convert_to_drive_file_object(cls, item):
        list_of_owners_dicts = item['owners']
        owners = [DriveApiUser(owner_dict) for owner_dict in list_of_owners_dicts]

        unknown_user = {DriveApiUserFields.EMAIL_ADDRESS: DriveApiUserFields.UNKNOWN_USER,
                        DriveApiUserFields.DISPLAY_NAME: DriveApiUserFields.UNKNOWN_USER}
        sharing_user_dict = item[DriveApiFileFields.SHARING_USER] if DriveApiFileFields.SHARING_USER in item else unknown_user
        sharing_user = DriveApiUser(sharing_user_dict)

        return DriveApiFile(item[DriveApiFileFields.ID],
                            item[DriveApiFileFields.NAME],
                            item[DriveApiFileFields.LINK],
                            item[DriveApiFileFields.CREATED_TIME],
                            item[DriveApiFileFields.MODIFIED_TIME],
                            item[DriveApiFileFields.SHARED_WITH_ME_TIME],
                            item[DriveApiFileFields.MIMETYPE], owners, sharing_user)

    @staticmethod
    def print_files(items):
        for item in items:
            LOG.info(u'{0} ({1})'.format(item[DriveApiFileFields.NAME], item[DriveApiFileFields.ID]))


class DriveAuthorizer:
    CREDENTIALS_FILENAME = 'credentials.json'
    TOKEN_FILENAME = 'token.pickle'
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']
    SERVER_PORT = 49555

    def __init__(self):
        pass

    def authorize(self):
        creds = self._load_token()
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            creds = self._handle_login(creds)
        return creds

    @classmethod
    def _load_token(cls):
        """
        The file token.pickle stores the user's access and refresh tokens, and is
        created automatically when the authorization flow completes for the first
        time.
        """
        creds = None
        if os.path.exists(cls.TOKEN_FILENAME):
            with open(cls.TOKEN_FILENAME, 'rb') as token:
                creds = pickle.load(token)
        return creds

    @classmethod
    def _handle_login(cls, creds):
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                cls.CREDENTIALS_FILENAME, cls.SCOPES)
            creds = flow.run_local_server(port=cls.SERVER_PORT)
        # Save the credentials for the next run
        cls._write_token(creds)
        return creds

    @classmethod
    def _write_token(cls, creds):
        with open(cls.TOKEN_FILENAME, 'wb') as token:
            pickle.dump(creds, token)