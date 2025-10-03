import streamlit as st

def list_folders_debug(parent_id):
    """List folders and log what we get from Drive API."""
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
        # Log folder info
        st.write(f"Found {len(folders)} folders in parent {parent_id}:")
        for f in folders:
            st.write(f" - {f['name']} ({f['id']})")
        all_folders.extend(folders)
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    return all_folders

# Example usage:
MAIN_FOLDER_ID = "1mO6EhBkG_lBbG2D5m8gUKHr4PftNXvds"
folders = list_folders_debug(MAIN_FOLDER_ID)
st.write("Total folders found:", len(folders))
