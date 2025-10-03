# streamlit_app.py
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from io import BytesIO
from docx import Document
import mammoth

# -------------------------
# Authenticate with Service Account
# -------------------------
# Ensure your Streamlit secrets has the service account JSON as "gcp_service_account"
creds_dict = st.secrets["gcp_service_account"]
credentials = service_account.Credentials.from_service_account_info(creds_dict)
service = build('drive', 'v3', credentials=credentials)

# -------------------------
# Helper Functions
# -------------------------
def list_folders(parent_id):
    """Return list of subfolders under a parent folder"""
    results = service.files().list(
        q=f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)"
    ).execute()
    return results.get('files', [])

def list_files(parent_id):
    """Return list of Word files (.docx or .doc) under a parent folder"""
    results = service.files().list(
        q=(
            f"'{parent_id}' in parents and trashed=false and "
            "(mimeType='application/vnd.google-apps.document' or "
            "mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document' or "
            "mimeType='application/msword')"
        ),
        fields="files(id, name, mimeType)"
    ).execute()
    return results.get('files', [])

def traverse_folder(parent_id, path=""):
    """Recursively get all recipes with paths"""
    items = []
    # Folders
    for folder in list_folders(parent_id):
        folder_path = f"{path}/{folder['name']}" if path else folder['name']
        items.extend(traverse_folder(folder['id'], folder_path))
    # Files
    for file in list_files(parent_id):
        file_path = f"{path}/{file['name']}" if path else file['name']
        items.append({"name": file['name'], "id": file['id'], "path": file_path, "mimeType": file['mimeType']})
    return items

def render_docx_from_drive(file_id):
    """Download a .docx from Drive and return HTML content"""
    request = service.files().export_media(fileId=file_id, mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    don
