from googleapiclient.discovery import build
from google.oauth2 import service_account
import streamlit as st
import json

def reset_all_drive_files():
    st.warning("⚠️ Suppression en cours de tous les fichiers du Drive...")

    SCOPES = ['https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT_INFO = json.loads(st.secrets["gdrive_key"])

    creds = service_account.Credentials.from_service_account_info(
        SERVICE_ACCOUNT_INFO, scopes=SCOPES)

    service = build('drive', 'v3', credentials=creds)

    # Lister tous les fichiers
    results = service.files().list(pageSize=1000, fields="files(id, name)").execute()
    items = results.get('files', [])
    st.info(f"🔎 Fichiers détectés : {len(items)}")

    if not items:
        st.success("✅ Aucun fichier à supprimer, Drive déjà vide.")
    else:
        for item in items:
            try:
                service.files().delete(fileId=item['id']).execute()
                st.info(f"🗑️ Supprimé : {item['name']}")
            except Exception as e:
                st.error(f"❌ Erreur en supprimant {item['name']} : {e}")

        st.success("🎉 Tous les fichiers ont été supprimés avec succès !")