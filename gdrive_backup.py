import os
import io
import json
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
import mimetypes
from googleapiclient.http import MediaFileUpload

def get_drive_service_from_secrets():
    service_account_info = json.loads(st.secrets["gdrive_key"])
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=credentials)

def restore_user_data(drive_service, local_data_dir, backup_folder_name, username):
    folder_query = f"name='{backup_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    folders = drive_service.files().list(q=folder_query, fields="files(id, name)").execute().get("files", [])
    if not folders:
        print("📁 Aucun dossier de sauvegarde trouvé sur Drive.")
        return

    backup_folder_id = folders[0]['id']
    user_folder_query = f"'{backup_folder_id}' in parents and name='{username}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    user_folders = drive_service.files().list(q=user_folder_query, fields="files(id, name)").execute().get("files", [])
    if not user_folders:
        print(f"📁 Aucun dossier utilisateur {username} trouvé sur Drive.")
        return

    user_folder_id = user_folders[0]['id']
    file_query = f"'{user_folder_id}' in parents and trashed=false"
    items = drive_service.files().list(q=file_query, fields="files(id, name, mimeType)").execute().get("files", [])

    os.makedirs(local_data_dir, exist_ok=True)

    for item in items:
        file_id = item['id']
        name = item['name']
        mime_type = item['mimeType']

        if mime_type == "application/vnd.google-apps.folder":
            subfolder_id = file_id
            subfolder_path = os.path.join(local_data_dir, name)
            os.makedirs(subfolder_path, exist_ok=True)
            sub_items = drive_service.files().list(q=f"'{subfolder_id}' in parents and trashed=false", fields="files(id, name)").execute().get("files", [])

            for sub in sub_items:
                sub_file_id = sub['id']
                sub_file_name = sub['name']
                sub_file_path = os.path.join(subfolder_path, sub_file_name)
                if not os.path.exists(sub_file_path):
                    request = drive_service.files().get_media(fileId=sub_file_id)
                    with io.FileIO(sub_file_path, "wb") as fh:
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()
        else:
            file_path = os.path.join(local_data_dir, name)
            if not os.path.exists(file_path):
                request = drive_service.files().get_media(fileId=file_id)
                with io.FileIO(file_path, "wb") as fh:
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()

def backup_user_data(drive_service, local_data_dir, backup_folder_name, username):
    def create_folder_if_not_exists(name, parent_id=None):
        query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        results = drive_service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])
        if files:
            return files[0]['id']
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        if parent_id:
            metadata["parents"] = [parent_id]
        folder = drive_service.files().create(body=metadata, fields="id").execute()
        return folder["id"]

    backup_folder_id = create_folder_if_not_exists(backup_folder_name)
    user_folder_id = create_folder_if_not_exists(username, backup_folder_id)

    for root, _, files in os.walk(local_data_dir):
        rel_path = os.path.relpath(root, local_data_dir)
        parent_id = user_folder_id
        if rel_path != ".":
            parent_id = create_folder_if_not_exists(rel_path, user_folder_id)

        for file_name in files:
            file_path = os.path.join(root, file_name)
            mime_type, _ = mimetypes.guess_type(file_path)
            metadata = {
                "name": file_name,
                "parents": [parent_id]
            }
            media = MediaFileUpload(file_path, mimetype=mime_type)
            # Supprime les anciens fichiers portant le même nom
            q = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            existing = drive_service.files().list(q=q, fields="files(id)").execute().get("files", [])
            for f in existing:
                drive_service.files().delete(fileId=f['id']).execute()
            drive_service.files().create(body=metadata, media_body=media, fields="id").execute()