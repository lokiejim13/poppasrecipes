import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from io import BytesIO
from docx import Document

# -------------------------
# Service Account Auth
# -------------------------
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
creds_dict = st.secrets["gcp_service_account"]
credentials = service_account.Credentials.from_service_account_info(
    creds_dict,
    scopes=SCOPES
)
service = build('drive', 'v3', credentials=credentials)

def refresh_credentials():
    if not credentials.valid or credentials.expired:
        credentials.refresh(Request())

# -------------------------
# Debug helpers for Drive
# -------------------------
def list_folders_debug(parent_id):
    refresh_credentials()
    all_folders = []
    page_token = None
    while True:
        results = service.files().list(
            q=f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="nextPageToken, files(id, name)",
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        folders = results.get('files', [])
        st.write(f"DEBUG: Found {len(folders)} folders in parent {parent_id}:")
        for f in folders:
            st.write(f" - {f['name']} ({f['id']})")
        all_folders.extend(folders)
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    return all_folders

def list_files_debug(parent_id):
    refresh_credentials()
    all_files = []
    mime_types = [
        'application/vnd.google-apps.document',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/pdf'
    ]
    mime_query = " or ".join([f"mimeType='{m}'" for m in mime_types])
    query = f"'{parent_id}' in parents and trashed=false and ({mime_query})"
    page_token = None
    while True:
        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType)",
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files = results.get('files', [])
        st.write(f"DEBUG: Found {len(files)} files in folder {parent_id}:")
        for f in files:
            st.write(f" - {f['name']} ({f['id']}) type={f['mimeType']}")
        all_files.extend(files)
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    return all_files

def traverse_folder_debug(parent_id, path=""):
    items = []
    for folder in list_folders_debug(parent_id):
        folder_path = f"{path}/{folder['name']}" if path else folder['name']
        items.extend(traverse_folder_debug(folder['id'], folder_path))
    for file in list_files_debug(parent_id):
        file_path = f"{path}/{file['name']}" if path else file['name']
        items.append({
            "name": file['name'],
            "id": file['id'],
            "path": file_path,
            "mimeType": file['mimeType']
        })
    return items

# -------------------------
# DOCX renderer
# -------------------------
def download_file_from_drive(file_id):
    refresh_credentials()
    try:
        request = service.files().get_media(fileId=file_id)
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return fh.read()
    except Exception:
        return None

def render_docx_to_html(file_bytes):
    doc = Document(BytesIO(file_bytes))
    html = ""
    for para in doc.paragraphs:
        style = para.style.name.lower()
        if 'heading' in style:
            level = style[-1] if style[-1].isdigit() else "2"
            html += f"<h{level}>{para.text}</h{level}>"
        else:
            paragraph_html = ""
            for run in para.runs:
                text = run.text
                if run.bold:
                    text = f"<b>{text}</b>"
                if run.italic:
                    text = f"<i>{text}</i>"
                paragraph_html += text
            html += f"<p>{paragraph_html}</p>"
    return html

def render_docx_from_drive(file_id):
    file_bytes = download_file_from_drive(file_id)
    if file_bytes:
        return render_docx_to_html(file_bytes)
    else:
        return "<p style='color:red'>Cannot render file — access denied or download failed.</p>"

# -------------------------
# Folder tree display
# -------------------------
def display_folder_tree(items):
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
            if mime_type == 'application/vnd.google-apps.document':
                doc_link = f"https://docs.google.com/document/d/{file_item['id']}/edit?usp=sharing"
                st.markdown(
                    f'<iframe src="{doc_link}?embedded=true" width="100%" height="600"></iframe>',
                    unsafe_allow_html=True
                )
            elif mime_type == 'application/pdf':
                file_url = f"https://drive.google.com/uc?id={file_item['id']}&export=download"
                st.markdown(f"[Open PDF]({file_url})")
            elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                html = render_docx_from_drive(file_item['id'])
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.warning("File type not supported.")

# -------------------------
# Streamlit App
# -------------------------
st.title("🍴 Poppa's Recipe Viewer")

MAIN_FOLDER_ID = "1mO6EhBkG_lBbG2D5m8gUKHr4PftNXvds"  # BrianKellyRecipes

try:
    all_recipes = traverse_folder_debug(MAIN_FOLDER_ID)
except Exception as e:
    st.error(f"Failed to load folders/files: {e}")
    all_recipes = []

st.write("=== DEBUG: Traversed Folder Tree ===")
for r in all_recipes:
    st.write(f"{r['path']} ({r['id']}) type={r['mimeType']}")

if not all_recipes:
    st.warning("No recipes found or some folders are inaccessible to the service account!")
else:
    st.info("Browse recipes by folder:")
    display_folder_tree(all_recipes)
