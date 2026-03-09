# drive_manager.py
import streamlit as st
import os
import io
import json
import requests
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload

# Scopes necessários
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/gmail.send'
]

def get_current_url():
    return "https://gestorideal.streamlit.app"

def _get_credentials_file():
    """Tenta carregar as credenciais do token.json local."""
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            if creds and creds.valid: return creds
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open('token.json', 'w') as token: token.write(creds.to_json())
                return creds
        except Exception: 
            if os.path.exists('token.json'): os.remove('token.json')
    return None

def _get_drive_service(force_new_auth=False):
    """Gerencia a conexão Google."""
    creds = _get_credentials_file()
    if creds: return build('drive', 'v3', credentials=creds)
    return None

def check_drive_connection():
    creds = _get_credentials_file()
    return creds is not None and creds.valid

def find_or_create_folder(folder_name, parent_folder_id):
    service = _get_drive_service()
    if not service:
        st.error("Falha ao inicializar o serviço do Google Drive.")
        return None
    try:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed=false"
        response = service.files().list(q=query, fields="files(id)").execute()
        files = response.get('files', [])
        if files: return files[0]['id']
        return service.files().create(body={'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_folder_id]}, fields='id').execute()['id']
    except Exception as e:
        st.error(f"Erro ao buscar/criar pasta '{folder_name}': {e}")
        return None

def get_date_folder_structure(parent_folder_id):
    """
    Cria uma estrutura de pastas baseada na data atual: YYYY / MMMM
    Ex: 2026 / Março
    Retorna o ID da pasta do mês.
    """
    now = datetime.now()
    year_str = str(now.year)
    meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    month_str = meses[now.month - 1]
    
    year_folder_id = find_or_create_folder(year_str, parent_folder_id)
    if not year_folder_id: return None
    
    month_folder_id = find_or_create_folder(month_str, year_folder_id)
    return month_folder_id

def setup_lead_folders(lead_name):
    """Cria a estrutura de pastas para um novo lead no Drive."""
    service = _get_drive_service()
    if not service: return None
    try:
        root_id = st.secrets["DRIVE_ROOT_FOLDER_ID"]
        leads_root = find_or_create_folder("CLIENTES_CRM", root_id)
        
        # Pasta principal do Cliente
        cliente_folder_id = find_or_create_folder(lead_name, leads_root)
        
        # Subpastas
        find_or_create_folder("CONTRATOS", cliente_folder_id)
        find_or_create_folder("DOCUMENTOS_GERAIS", cliente_folder_id)
        find_or_create_folder("PROPOSTAS", cliente_folder_id)
        
        return cliente_folder_id
    except Exception: return None

def upload_file(file_object, file_name, destination_folder_id):
    service = _get_drive_service()
    if not service: return None
    try:
        media = MediaIoBaseUpload(io.BytesIO(file_object.getvalue()), mimetype=file_object.type, resumable=True)
        uploaded_file = service.files().create(body={'name': file_name, 'parents': [destination_folder_id]}, media_body=media, fields='id, webViewLink').execute()
        return {"id": uploaded_file.get("id"), "link": uploaded_file.get("webViewLink")}
    except Exception: return None

def update_file(file_id, file_object):
    """Atualiza o conteúdo de um arquivo existente."""
    service = _get_drive_service()
    if not service: return False
    try:
        media = MediaIoBaseUpload(io.BytesIO(file_object.getvalue()), mimetype=file_object.type, resumable=True)
        service.files().update(fileId=file_id, media_body=media).execute()
        return True
    except Exception: return False

def create_backup_snapshot(file_object=None):
    """
    Realiza o backup do database.xlsx para o Drive.
    Aceita um file_object opcional para compatibilidade.
    """
    service = _get_drive_service()
    if not service: return False
    try:
        root_id = st.secrets["DRIVE_ROOT_FOLDER_ID"]
        backups_folder_id = find_or_create_folder("BACKUPS_SISTEMA", root_id)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        backup_name = f"backup_projeto_ideal_{timestamp}.xlsx"
        
        from config import DATABASE_PATH
        # Se um objeto de arquivo for passado, usa ele. Caso contrário, lê do disco.
        if file_object:
            media = MediaIoBaseUpload(io.BytesIO(file_object.getvalue()), mimetype=file_object.type, resumable=True)
        else:
            media = MediaFileUpload(DATABASE_PATH, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        
        service.files().create(
            body={'name': backup_name, 'parents': [backups_folder_id]},
            media_body=media,
            fields='id'
        ).execute()
        return True
    except Exception as e:
        st.error(f"Erro no Backup: {e}")
        return False
