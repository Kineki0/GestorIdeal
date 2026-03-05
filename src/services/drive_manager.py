# drive_manager.py
import streamlit as st
import os
import io
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Scopes necessários
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/gmail.send'
]

def get_current_url():
    return "https://gestorideal.streamlit.app"

def _get_credentials_no_widgets():
    """Tenta carregar as credenciais sem causar warnings ou usar widgets."""
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            if creds and creds.valid:
                return creds
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
                return creds
        except Exception:
            if os.path.exists('token.json'): os.remove('token.json')
    return None

def _get_drive_service(force_new_auth=False):
    """Gerencia a conexão com o Google Drive de forma resiliente para nuvem."""
    if force_new_auth:
        if os.path.exists('token.json'): os.remove('token.json')
        st.cache_resource.clear()

    creds = _get_credentials_no_widgets()
    if creds:
        return build('drive', 'v3', credentials=creds)

    # --- FLUXO DE AUTORIZAÇÃO (Callback) ---
    client_config = None
    if "GCP_CLIENT_SECRETS" in st.secrets:
        client_config = json.loads(st.secrets["GCP_CLIENT_SECRETS"])
    elif os.path.exists('client_secrets.json'):
        with open('client_secrets.json', 'r') as f:
            client_config = json.load(f)

    if not client_config:
        st.error("❌ Credenciais do Google não encontradas.")
        return None

    # Redirect URI deve ser EXATAMENTE a URL do app
    redirect_uri = get_current_url()
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)

    # CAPTURA DO CÓDIGO (Quando o Google volta para o app)
    auth_code = st.query_params.get("code")
    
    if auth_code:
        try:
            # Na nuvem, o 'state' pode se perder. 
            # Se falhar com state, tentamos sem (menos seguro mas funcional na nuvem)
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao processar código: {e}")
            st.info("Dica: Tente clicar em autorizar novamente.")
            st.query_params.clear()
            return None
    else:
        # Se não logado e sem código, mostra o botão
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        
        st.info("🔒 É necessário autorizar o acesso ao Google.")
        # Usamos link_button que é a forma oficial do Streamlit de redirecionar
        st.link_button("🔗 CLIQUE AQUI PARA CONECTAR AO GOOGLE", auth_url, use_container_width=True)
        st.stop()
    
    return None

def check_drive_connection():
    """Verifica conexão ativa."""
    creds = _get_credentials_no_widgets()
    return creds is not None and creds.valid

def find_or_create_folder(folder_name, parent_folder_id):
    service = _get_drive_service()
    if not service: return None
    try:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed=false"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = response.get('files', [])
        if files: return files[0].get('id')
        return service.files().create(body={'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_folder_id]}, fields='id').execute().get('id')
    except Exception: return None

def get_date_folder_structure(root_id):
    now = datetime.now()
    ano_id = find_or_create_folder(str(now.year), root_id)
    if not ano_id: return root_id
    mes_id = find_or_create_folder(now.strftime('%B').capitalize(), ano_id)
    return mes_id if mes_id else ano_id

def upload_file(file_object, file_name, destination_folder_id):
    service = _get_drive_service()
    if not service: return None
    try:
        media = MediaIoBaseUpload(io.BytesIO(file_object.getvalue()), mimetype=file_object.type, resumable=True)
        uploaded_file = service.files().create(body={'name': file_name, 'parents': [destination_folder_id]}, media_body=media, fields='id, webViewLink').execute()
        return {"id": uploaded_file.get("id"), "link": uploaded_file.get("webViewLink")}
    except Exception: return None

def update_file(file_id, file_object):
    service = _get_drive_service()
    if not service: return None
    try:
        media = MediaIoBaseUpload(io.BytesIO(file_object.getvalue()), mimetype=file_object.type, resumable=True)
        updated_file = service.files().update(fileId=file_id, media_body=media, fields='id, webViewLink').execute()
        return {"id": updated_file.get("id"), "link": updated_file.get("webViewLink")}
    except Exception: return None
