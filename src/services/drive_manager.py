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
    Suporta o fluxo de redirecionamento necessário para o Streamlit Cloud.
    """
    if force_new_auth and os.path.exists('token.json'):
        os.remove('token.json')

    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Se tivermos credenciais e elas forem válidas, retornamos o serviço
    if creds and creds.valid:
        return build('drive', 'v3', credentials=creds)

    # Se expiraram, tentamos renovar
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            return build('drive', 'v3', credentials=creds)
        except Exception:
            if os.path.exists('token.json'): os.remove('token.json')

    # --- FLUXO DE AUTORIZAÇÃO (CASO NÃO TENHA TOKEN VÁLIDO) ---
    
    # 1. Carrega configuração do segredo ou arquivo local
    client_config = None
    if "GCP_CLIENT_SECRETS" in st.secrets:
        client_config = json.loads(st.secrets["GCP_CLIENT_SECRETS"])
    elif os.path.exists('client_secrets.json'):
        with open('client_secrets.json', 'r') as f:
            client_config = json.load(f)

    if not client_config:
        st.error("❌ Credenciais do Google não encontradas.")
        return None

    # Define a URL de redirecionamento (deve bater com a do Google Console)
    # No Streamlit Cloud, o ideal é usar a URL principal do app
    redirect_uri = "https://gestor-ideal.streamlit.app"
    
    flow = Flow.from_client_config(
        client_config, 
        scopes=SCOPES, 
        redirect_uri=redirect_uri
    )

    # Verifica se o código de autorização está na URL (redirecionado pelo Google)
    auth_code = st.query_params.get("code")
    
    if auth_code:
        try:
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            st.query_params.clear() # Limpa a URL
            st.success("✅ Autorização concluída com sucesso! Atualizando...")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao processar código de autorização: {e}")
            return None
    else:
        # Se não há código na URL, exibe o botão de autorização
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        
        st.info("🔒 A conexão com o Google Drive/Gmail precisa ser autorizada.")
        st.link_button("🔗 CLIQUE AQUI PARA AUTORIZAR", auth_url, use_container_width=True)
        st.warning("⚠️ Na tela de aviso, clique em 'Configurações Avançadas' e depois em 'Ir para Ideal CRM (não seguro)'.")
        st.stop() # Interrompe a execução até que o usuário autorize

    return None

def check_drive_connection():
    """Verifica se a conexão está ativa."""
    try:
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            return creds and creds.valid
        return False
    except Exception:
        return False

# --- Funções de Pasta e Arquivo (Mantidas iguais) ---

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
