# drive_manager.py
import streamlit as st
import os
import io
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Scopes necessários para gerenciar arquivos no Drive e enviar e-mails
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/gmail.send'
]

# --- Autenticação OAuth 2.0 (Nuvem + Local) ---
@st.cache_resource(show_spinner="Conectando ao Google...")
def _get_drive_service(force_new_auth=False):
    """
    Autentica na API do Google Drive usando OAuth 2.0.
    Suporta leitura de client_secrets via arquivo local ou Streamlit Secrets.
    """
    if force_new_auth and os.path.exists('token.json'):
        os.remove('token.json')

    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                if os.path.exists('token.json'): os.remove('token.json')
                return _get_drive_service(force_new_auth=True)
        else:
            # 1. Tenta obter credenciais do segredo do Streamlit Cloud
            client_config = None
            if "GCP_CLIENT_SECRETS" in st.secrets:
                try:
                    client_config = json.loads(st.secrets["GCP_CLIENT_SECRETS"])
                except Exception as e:
                    st.error(f"Erro ao ler segredo GCP_CLIENT_SECRETS: {e}")
            
            # 2. Se não estiver nos segredos, procura o arquivo local
            if not client_config and os.path.exists('client_secrets.json'):
                with open('client_secrets.json', 'r') as f:
                    client_config = json.load(f)

            if not client_config:
                st.error("❌ Credenciais do Google (client_secrets) não encontradas nos segredos nem em arquivo local.")
                return None

            # Inicia o fluxo de autorização
            # No Streamlit Cloud, o flow.run_local_server pode não abrir o navegador.
            # Usamos redirect_uri do localhost como padrão.
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            
            try:
                # O open_browser=True tentará abrir no computador de quem está acessando
                creds = flow.run_local_server(port=0, open_browser=True, prompt='consent')
            except Exception as e:
                st.error(f"Erro no fluxo de autorização: {e}")
                st.info("Dica: Se estiver na nuvem, certifique-se de que a URL do seu app está nos 'URIs de redirecionamento' do Google Cloud Console.")
                return None
            
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Erro ao construir serviço Google: {e}")
        return None

def check_drive_connection():
    """Verifica se o token atual possui as permissões necessárias."""
    try:
        service = _get_drive_service()
        if not service: return False
        
        if not os.path.exists('token.json'): return False
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        scopes = creds.scopes if creds.scopes else []
        drive_ok = 'https://www.googleapis.com/auth/drive' in scopes
        gmail_ok = 'https://www.googleapis.com/auth/gmail.send' in scopes
        
        if drive_ok and gmail_ok:
            return True
        return False
    except Exception:
        return False

# --- Funções de Pasta e Arquivo ---

def find_or_create_folder(folder_name, parent_folder_id):
    service = _get_drive_service()
    if not service: return None
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed=false"
    try:
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])
        if files: return files[0].get('id')
        
        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_folder_id]}
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    except Exception as e:
        st.error(f"Erro na pasta: {e}")
        return None

def get_date_folder_structure(root_id):
    """Retorna o ID da pasta do mês atual, criando a estrutura Ano/Mês se necessário."""
    now = datetime.now()
    ano_str = str(now.year)
    mes_str = now.strftime('%B').capitalize()
    
    ano_id = find_or_create_folder(ano_str, root_id)
    if not ano_id: return root_id
    
    mes_id = find_or_create_folder(mes_str, ano_id)
    return mes_id if mes_id else ano_id

def upload_file(file_object, file_name, destination_folder_id):
    service = _get_drive_service()
    if not service: return None
    try:
        media = MediaIoBaseUpload(io.BytesIO(file_object.getvalue()), mimetype=file_object.type, resumable=True)
        file_metadata = {'name': file_name, 'parents': [destination_folder_id]}
        uploaded_file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        return {"id": uploaded_file.get("id"), "link": uploaded_file.get("webViewLink")}
    except Exception as e:
        st.error(f"Erro no upload: {e}")
        return None

def update_file(file_id, file_object):
    service = _get_drive_service()
    if not service: return None
    try:
        media = MediaIoBaseUpload(io.BytesIO(file_object.getvalue()), mimetype=file_object.type, resumable=True)
        updated_file = service.files().update(fileId=file_id, media_body=media, fields='id, webViewLink').execute()
        return {"id": updated_file.get("id"), "link": updated_file.get("webViewLink")}
    except Exception as e:
        st.error(f"Erro no update: {e}")
        return None
