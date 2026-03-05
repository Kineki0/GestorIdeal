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
    """Gerencia a conexão Google usando fluxo de redirecionamento automático (Polido)."""
    if force_new_auth and os.path.exists('token.json'):
        os.remove('token.json')
        st.cache_resource.clear()

    creds = _get_credentials_file()
    if creds: return build('drive', 'v3', credentials=creds)

    # --- FLUXO DE AUTORIZAÇÃO ---
    client_config = None
    if "GCP_CLIENT_SECRETS" in st.secrets:
        client_config = json.loads(st.secrets["GCP_CLIENT_SECRETS"])
    elif os.path.exists('client_secrets.json'):
        with open('client_secrets.json', 'r') as f: client_config = json.load(f)

    if not client_config:
        st.error("❌ Credenciais do Google não configuradas.")
        return None

    # Configura o Flow
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=get_current_url())
    
    # CAPTURA DO CÓDIGO DA URL
    auth_code = st.query_params.get("code")
    
    if auth_code:
        # Recupera o verificador do session_state
        verifier = st.session_state.get('oauth_verifier')
        
        if verifier:
            try:
                flow.fetch_token(code=auth_code, code_verifier=verifier)
                with open('token.json', 'w') as token:
                    token.write(flow.credentials.to_json())
                st.query_params.clear()
                if 'oauth_verifier' in st.session_state: del st.session_state['oauth_verifier']
                st.success("✅ Conectado com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Falha na sincronização: {e}")
                st.query_params.clear()
        else:
            # Fallback amigável: se perdeu o verifier, pede para o usuário um último clique
            st.warning("👋 Quase lá! O Google já autorizou.")
            if st.button("🚀 CLIQUE AQUI PARA FINALIZAR A CONEXÃO", type="primary", use_container_width=True):
                # Tentativa sem verifier (algumas configs de Google Cloud permitem)
                try:
                    flow.fetch_token(code=auth_code)
                    with open('token.json', 'w') as token:
                        token.write(flow.credentials.to_json())
                    st.query_params.clear()
                    st.success("✅ Conectado!")
                    st.rerun()
                except:
                    st.error("Erro de segurança. Por favor, tente conectar novamente.")
                    st.query_params.clear()
        st.stop()
    else:
        # Tela inicial de conexão
        st.subheader("👋 Conectar ao Google Drive")
        st.info("Para salvar e carregar os dados com segurança, precisamos da sua autorização.")
        
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        
        # Guarda o verifier ANTES de sair
        st.session_state['oauth_verifier'] = flow.code_verifier
        
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
