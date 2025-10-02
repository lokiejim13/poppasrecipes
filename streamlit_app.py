import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

# -------------------------
# Authenticate with service account via Streamlit secrets
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
    st.warning(results.get('files', []))
    return results.get('files', [])

def list_files(parent_id):
    results = service.files().list(
        q=f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false",
        fields="files(id, name)"
    ).execute()
    return results.get('files', [])

def traverse_folder(parent_id, path=""):
    items = []
    for folder in list_folders(parent_id):
        folder_path = f"{path}/{folder['name']}" if path else folder['name']
        items.extend(traverse_folder(folder['id'], folder_path))
    for file in list_files(parent_id):
        file_path = f"{path}/{file['name']}" if path else file['name']
        items.append({"name": file['name'], "id": file['id'], "path": file_path})
    return items

# -------------------------
# Streamlit App
# -------------------------
st.title("🍴 Poppa's Recipe Viewer")

MAIN_FOLDER_ID = "1mO6EhBkG_lBbG2D5m8gUKHr4PftNXvds"  # BrianKellyRecipes

all_recipes = traverse_folder(MAIN_FOLDER_ID)

if not all_recipes:
    st.warning("No recipes found!")
else:
    recipe_paths = [r['path'] for r in all_recipes]
    selected_path = st.selectbox("Select a recipe", recipe_paths)

    selected_recipe = next(r for r in all_recipes if r['path'] == selected_path)
    recipe_id = selected_recipe['id']

    doc_link = f"https://docs.google.com/document/d/{recipe_id}/edit?usp=sharing"
    st.markdown(
        f'<iframe src="{doc_link}?embedded=true" width="100%" height="600"></iframe>',
        unsafe_allow_html=True
    )
