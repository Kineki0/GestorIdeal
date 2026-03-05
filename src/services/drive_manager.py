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
import extra_streamlit_components as stx

# Scopes necessários
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/gmail.send'
]

def get_current_url():
    """URL oficial do app na nuvem."""
    return "https://gestorideal.streamlit.app"

def _get_cookie_manager():
    """Gerenciador de cookies para persistência de segurança."""
    if 'stx_cookie_manager' not in st.session_state:
        st.session_state.stx_cookie_manager = stx.CookieManager()
    return st.session_state.stx_cookie_manager

def _get_credentials_file():
    """Carrega o token silenciosamente se ele existir."""
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
    """Fluxo de conexão totalmente automático e amigável para o cliente."""
    if force_new_auth and os.path.exists('token.json'):
        os.remove('token.json')
        st.cache_resource.clear()

    creds = _get_credentials_file()
    if creds: return build('drive', 'v3', credentials=creds)

    # --- FLUXO AUTOMÁTICO (Client Friendly) ---
    client_config = None
    if "GCP_CLIENT_SECRETS" in st.secrets:
        client_config = json.loads(st.secrets["GCP_CLIENT_SECRETS"])
    elif os.path.exists('client_secrets.json'):
        with open('client_secrets.json', 'r') as f: client_config = json.load(f)

    if not client_config:
        st.error("❌ Erro: Credenciais do Google não configuradas.")
        return None

    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=get_current_url())
    cookie_manager = _get_cookie_manager()
    
    # 1. Verifica se o Google enviou o código de volta pela URL
    auth_code = st.query_params.get("code")
    
    if auth_code:
        # Recupera o verificador do cookie (gerado antes do redirecionamento)
        verifier = cookie_manager.get('oauth_v')
        
        if verifier:
            with st.spinner("🚀 Finalizando conexão segura..."):
                try:
                    flow.fetch_token(code=auth_code, code_verifier=verifier)
                    with open('token.json', 'w') as token:
                        token.write(flow.credentials.to_json())
                    st.query_params.clear()
                    cookie_manager.delete('oauth_v')
                    st.rerun()
                except Exception as e:
                    st.error("Falha ao validar login. Por favor, tente novamente.")
                    st.query_params.clear()
        else:
            # Se o cookie ainda não carregou, recarrega a página para forçar a leitura
            st.info("🔄 Sincronizando com o Google...")
            st.rerun()
    else:
        # 2. Se não está conectado, mostra o botão elegante
        st.subheader("👋 Bem-vindo ao Gestor Ideal")
        st.write("Para começar, precisamos conectar sua conta Google para salvar os arquivos com segurança.")
        
        auth_url, state = flow.authorization_url(prompt='consent', access_type='offline')
        
        # O pulo do gato: salvar o verifier no cookie ANTES de clicar
        cookie_manager.set('oauth_v', flow.code_verifier, key="set_v")
        
        if st.link_button("🔗 CONECTAR GOOGLE DRIVE", auth_url, use_container_width=True, type="primary"):
            pass # O link_button já faz o redirecionamento
        
        st.stop()
    
    return None

def check_drive_connection():
    creds = _get_credentials_file()
    return creds is not None and creds.valid

def find_or_create_folder(folder_name, parent_folder_id):
    service = _get_drive_service()
    if not service: return None
    try:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{parent_folder_id}' in parents and trashed=false"
        response = service.files().list(q=query, fields="files(id)").execute()
        files = response.get('files', [])
        if files: return files[0]['id']
        return service.files().create(body={'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_folder_id]}, fields='id').execute()['id']
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
