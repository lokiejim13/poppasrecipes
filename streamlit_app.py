# streamlit_app.py
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

# -------------------------
# Authenticate with Service Account
# -------------------------
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

def list_docs(parent_id):
    """Return list of Google Docs or Word files under a parent folder"""
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
    """Recursively build folder tree"""
    items = []
    for folder in list_folders(parent_id):
        folder_path = f"{path}/{folder['name']}" if path else folder['name']
        items.extend(traverse_folder(folder['id'], folder_path))
    for file in list_docs(parent_id):
        file_path = f"{path}/{file['name']}" if path else file['name']
        items.append({"name": file['name'], "id": file['id'], "path": file_path, "mimeType": file['mimeType']})
    return items

def display_folder_tree(items):
    """Display collapsible folder tree with iframe embedding"""
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
            # Use Google Docs preview iframe
            doc_link = f"https://docs.google.com/document/d/{file_item['id']}/preview"
            st.markdown(
                f'<iframe src="{doc_link}" width="100%" height="600"></iframe>',
                unsafe_allow_html=True,
            )

# -------------------------
# Streamlit App
# -------------------------
st.title("🍴 Poppa's Recipe Viewer")

# Replace with your Google Drive folder ID
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
