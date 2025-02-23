import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# Define the scope for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate_drive():
    creds = None

    # Remove existing token.json to start fresh
    if os.path.exists('token.json'):
        os.remove('token.json')

    # Check if credentials.json exists
    if not os.path.exists('credentials.json'):
        raise FileNotFoundError("The 'credentials.json' file is missing.")

    # Initiate the flow to obtain credentials
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    flow.access_type = 'offline'  # Request a refresh token
    flow.prompt = 'consent'       # Force consent screen to ensure refresh token is received
    creds = flow.run_local_server(port=8082)

    # Save the credentials for future use
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)
# Call the function to authenticate and create the drive service
# authenticate_drive()


def upload_to_drive(file_path, file_name):
    """Uploads a file to the 'Job Resume' folder in Google Drive and returns the file link."""
    service = authenticate_drive()

    # Define the folder name
    folder_name = 'Job Resume'

    # Search for the folder in Google Drive
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])

    if items:
        # Folder exists
        folder_id = items[0]['id']
    else:
        # Folder does not exist; create it
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        folder_id = folder.get('id')

    # Upload the file to the specified folder
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, mimetype='application/pdf')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    # Generate the file link
    file_link = f'https://drive.google.com/file/d/{file["id"]}/view'
    return file_link
