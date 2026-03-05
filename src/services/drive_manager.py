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
from googleapiclient.http import MediaIoBaseUpload

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
    """Gerencia a conexão Google usando fluxo HTTP Direto (Mais estável para nuvem)."""
    if force_new_auth and os.path.exists('token.json'):
        os.remove('token.json')
        st.cache_resource.clear()

    creds = _get_credentials_file()
    if creds: return build('drive', 'v3', credentials=creds)

    # --- FLUXO DE AUTORIZAÇÃO DIRETO ---
    client_config = None
    if "GCP_CLIENT_SECRETS" in st.secrets:
        client_config = json.loads(st.secrets["GCP_CLIENT_SECRETS"]).get('web')
    elif os.path.exists('client_secrets.json'):
        with open('client_secrets.json', 'r') as f: 
            client_config = json.load(f).get('web')

    if not client_config:
        st.error("❌ Credenciais do Google não configuradas corretamente nos Secrets.")
        return None

    auth_code = st.query_params.get("code")
    
    if auth_code:
        # TROCA O CÓDIGO PELO TOKEN VIA HTTP (Bypassa o erro de verifier)
        with st.spinner("🚀 Finalizando conexão..."):
            try:
                response = requests.post('https://oauth2.googleapis.com/token', data={
                    'code': auth_code,
                    'client_id': client_config['client_id'],
                    'client_secret': client_config['client_secret'],
                    'redirect_uri': get_current_url(),
                    'grant_type': 'authorization_code'
                })
                
                token_data = response.json()
                if 'access_token' in token_data:
                    # Cria objeto de credenciais e salva no token.json
                    new_creds = Credentials(
                        token=token_data['access_token'],
                        refresh_token=token_data.get('refresh_token'),
                        token_uri='https://oauth2.googleapis.com/token',
                        client_id=client_config['client_id'],
                        client_secret=client_config['client_secret'],
                        scopes=SCOPES
                    )
                    with open('token.json', 'w') as f:
                        f.write(new_creds.to_json())
                    
                    st.query_params.clear()
                    st.success("✅ Conectado com sucesso!")
                    st.rerun()
                else:
                    st.error(f"Erro no Google: {token_data.get('error_description', 'Falha desconhecida')}")
                    st.query_params.clear()
            except Exception as e:
                st.error(f"Erro técnico: {e}")
                st.query_params.clear()
    else:
        # Mostra o botão de conexão amigável
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_config['client_id']}&"
            f"redirect_uri={get_current_url()}&"
            f"response_type=code&"
            f"scope={' '.join(SCOPES)}&"
            f"access_type=offline&prompt=consent"
        )
        
        st.subheader("👋 Conectar ao Google")
        st.info("Para salvar seus dados, precisamos de uma rápida autorização na sua conta Google.")
        st.link_button("🔗 CLIQUE AQUI PARA AUTORIZAR", auth_url, use_container_width=True)
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
