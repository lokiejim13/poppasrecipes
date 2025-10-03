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
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    document = Document(fh)
    html = ""
    for para in document.paragraphs:
        html += f"<p>{para.text}</p>"
    return html

def display_folder_tree(items):
    """Render collapsible folder tree with clickable files"""
    folder_map = {}
    file_map = {}
    for item in items:
        path_parts = item['path'].split('/')
        if len(path_parts) == 1:
            file_map[path_parts[0]] = item
        else:
            folder_name = path_parts[0]
            remaining_path = '/'.join(path_parts[1:])
            folder_map.setdefault(folder_name, []).append({**item, 'path': remaining_path})

    # Display folders
    for folder_name, folder_items in folder_map.items():
        with st.expander(f"📁 {folder_name}", expanded=False):
            display_folder_tree(folder_items)

    # Display files
    for file_name, file_item in file_map.items():
        if st.button(f"📄 {file_item['name']}", key=file_item['id']):
            mime_type = file_item['mimeType']
            if mime_type == 'application/vnd.google-apps.document' or mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                html = render_docx_from_drive(file_item['id'])
                st.markdown(html, unsafe_allow_html=True)
            elif mime_type == 'application/msword':
                # Provide download link for old .doc files
                file_url = f"https://drive.google.com/uc?id={file_item['id']}&export=download"
                st.markdown(f"[Download {file_item['name']}]({file_url})")
            else:
                st.warning("File type not supported.")

# -------------------------
# Streamlit App
# -------------------------
st.title("🍴 Poppa's Recipe Viewer")

# Top-level folder ID for BrianKellyRecipes
MAIN_FOLDER_ID = "1mO6EhBkG_lBbG2D5m8gUKHr4PftNXvds"

with st.spinner("Loading folders and recipes..."):
    try:
        all_recipes = traverse_folder(MAIN_FOLDER_ID)
        st.success(f"Found {len(all_recipes)} recipes!")
    except Exception as e:
        st.error(f"Failed to load folders/files: {e}")
        all_recipes = []

if all_recipes:
    st.write("Browse recipes by folder:")
    display_folder_tree(all_recipes)
else:
    st.warning("No recipes found!")
