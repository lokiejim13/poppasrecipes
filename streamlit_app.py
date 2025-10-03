import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
from io import BytesIO
from docx import Document
import base64

# -------------------------
# Authenticate with service account
# -------------------------
creds_dict = st.secrets["gcp_service_account"]
credentials = service_account.Credentials.from_service_account_info(creds_dict)
service = build('drive', 'v3', credentials=credentials)

# -------------------------
# Helper Functions
# -------------------------
def list_folders(parent_id):
    results = service.files().list(
        q=f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)"
    ).execute()
    return results.get('files', [])

def list_files(parent_id):
    mime_types = [
        'application/vnd.google-apps.document',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/pdf'
    ]
    mime_query = " or ".join([f"mimeType='{m}'" for m in mime_types])
    query = f"'{parent_id}' in parents and trashed=false and ({mime_query})"
    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType)"
    ).execute()
    return results.get('files', [])

def traverse_folder(parent_id, path=""):
    items = []
    for folder in list_folders(parent_id):
        folder_path = f"{path}/{folder['name']}" if path else folder['name']
        items.extend(traverse_folder(folder['id'], folder_path))
    for file in list_files(parent_id):
        file_path = f"{path}/{file['name']}" if path else file['name']
        items.append({
            "name": file['name'],
            "id": file['id'],
            "path": file_path,
            "mimeType": file['mimeType']
        })
    return items

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

    # Images
    for shape in doc.inline_shapes:
        try:
            image_stream = BytesIO()
            shape._inline.graphic.graphicData.pic.blipFill.blip._blip.save(image_stream)
            b64 = base64.b64encode(image_stream.getvalue()).decode()
            html += f'<img src="data:image/png;base64,{b64}"><br>'
        except Exception:
            continue
    return html

def render_docx_from_drive(file_id):
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    headers = {"Authorization": f"Bearer {credentials.token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return render_docx_to_html(response.content)

def display_folder_tree(items, parent_path=""):
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

    # Folders
    for folder_name, folder_items in folder_map.items():
        with st.expander(f"📁 {folder_name}", expanded=False):
            display_folder_tree(folder_items)

    # Files
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
                st.info("Rendering Word document:")
                html = render_docx_from_drive(file_item['id'])
                st.markdown(html, unsafe_allow_html=True)

# -------------------------
# Streamlit App
# -------------------------
st.title("🍴 Poppa's Recipe Viewer")

MAIN_FOLDER_ID = "1mO6EhBkG_lBbG2D5m8gUKHr4PftNXvds"
all_recipes = traverse_folder(MAIN_FOLDER_ID)

if not all_recipes:
    st.warning("No recipes found!")
else:
    st.info("Browse recipes by folder:")
    display_folder_tree(all_recipes)
