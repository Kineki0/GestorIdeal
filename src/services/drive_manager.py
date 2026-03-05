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
    """Gerencia a conexão Google usando fluxo de código manual (Infalível na nuvem)."""
    if force_new_auth and os.path.exists('token.json'):
        os.remove('token.json')

    creds = _get_credentials_file()
    if creds: return build('drive', 'v3', credentials=creds)

    # --- FLUXO MANUAL ---
    client_config = None
    if "GCP_CLIENT_SECRETS" in st.secrets:
        client_config = json.loads(st.secrets["GCP_CLIENT_SECRETS"])
    elif os.path.exists('client_secrets.json'):
        with open('client_secrets.json', 'r') as f: client_config = json.load(f)

    if not client_config:
        st.error("❌ Credenciais do Google não encontradas nos Secrets.")
        return None

    # Usamos o redirecionamento para o localhost como sinal de fluxo manual
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri='http://localhost')
    
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    
    st.subheader("🔗 Conectar ao Google Drive")
    st.info("O sistema precisa de autorização para salvar seus dados.")
    
    st.markdown(f"1. [CLIQUE AQUI para abrir a página de autorização]({auth_url})")
    st.markdown("2. Faça o login e clique em **Continuar/Permitir**.")
    st.markdown("3. Você será enviado para uma página que 'não carrega' ou dá erro. **NÃO SE PREOCUPE!**")
    st.markdown("4. Vá na barra de endereços do seu navegador, procure por **code=...** e copie tudo o que vem depois do igual até o próximo símbolo de &.")
    
    auth_code = st.text_input("5. Cole o código de autorização aqui:")
    
    if st.button("FINALIZAR CONEXÃO", type="primary", use_container_width=True):
        if auth_code:
            try:
                flow.fetch_token(code=auth_code)
                with open('token.json', 'w') as token:
                    token.write(flow.credentials.to_json())
                st.success("✅ Conectado com sucesso! Recarregando...")
                st.rerun()
            except Exception as e:
                st.error(f"Código inválido. Por favor, tente novamente. ({e})")
        else:
            st.warning("Insira o código gerado pelo Google.")
    
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
