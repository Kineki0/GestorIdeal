# repository_excel.py
import pandas as pd
import os
import io
import streamlit as st
import openpyxl
import config
import threading
import json
from datetime import datetime, timedelta
from config import ETAPAS_KANBAN as DEFAULT_ETAPAS
import utils
import secrets
from googleapiclient.http import MediaIoBaseDownload

# Lock para evitar race conditions
from threading import Lock
excel_lock = Lock()

# --- Funções de Sincronização Google Drive ---

def _sync_from_drive():
    from services import drive_manager
    try:
        root_id = st.secrets["DRIVE_ROOT_FOLDER_ID"]
        service = drive_manager._get_drive_service()
        if not service: return False
        query = f"name='database.xlsx' and '{root_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        if files:
            file_id = files[0]['id']
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                _, done = downloader.next_chunk()
            os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)
            with open(config.DATABASE_PATH, 'wb') as f:
                f.write(fh.getvalue())
            return True
    except Exception: pass
    return False

def _sync_worker():
    try:
        from services import drive_manager
        root_id = st.secrets["DRIVE_ROOT_FOLDER_ID"]
        service = drive_manager._get_drive_service()
        if not service: return
        query = f"name='database.xlsx' and '{root_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id)").execute()
        files = results.get('files', [])
        if not os.path.exists(config.DATABASE_PATH): return
        with open(config.DATABASE_PATH, 'rb') as f:
            content = f.read()
        class MockFile:
            def __init__(self, c): self.c = c
            def getvalue(self): return self.c
            @property
            def type(self): return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        mock = MockFile(content)
        if files:
            drive_manager.update_file(files[0]['id'], mock)
        else:
            drive_manager.upload_file(mock, "database.xlsx", root_id)
    except Exception: pass

def _sync_to_drive_async():
    threading.Thread(target=_sync_worker).start()

# --- Funções de Leitura e Escrita ---

def _load_database_from_file():
    _sync_from_drive()
    
    expected_lead_columns = [
        'ID_Lead', 'Razao_Social', 'Telefone', 'Nome_Contato', 'CNPJ', 'Email', 
        'Etapa_Atual', 'Status', 'Prioridade', 'Risco', 'Esforco', 'Nucleo',
        'Data_Criacao', 'Ultima_Atualizacao', 'Data_Entrada_Etapa', 'Prazo', 
        'Descricao', 'Checklist'
    ]

    if not os.path.exists(config.DATABASE_PATH):
        dfs = {
            'Usuarios': pd.DataFrame({'ID_Usuario': [], 'Nome': [], 'Email': [], 'Senha': [], 'Perfil': [], 'Ativo': []}),
            'Leads': pd.DataFrame(columns=expected_lead_columns),
            'Historico': pd.DataFrame({'ID_Historico': [], 'ID_Lead': [], 'Timestamp': [], 'Usuario': [], 'Tipo': [], 'Campo': [], 'Antigo': [], 'Novo': [], 'Mensagem': []}),
            'Anexos': pd.DataFrame({'ID_Anexo': [], 'Tipo_Referencia': [], 'ID_Referencia': [], 'Nome_Arquivo': [], 'Link_Drive': [], 'Usuario_Envio': [], 'Data_Envio': []}),
            'Logs': pd.DataFrame({'Timestamp': [], 'Nivel': [], 'Mensagem': []}),
            'PasswordResetTokens': pd.DataFrame({'Token': [], 'Email': [], 'ExpiresAt': [], 'Used': []}),
            'KanbanConfig': pd.DataFrame({'ID_Etapa': [i+1 for i in range(len(DEFAULT_ETAPAS))], 'Nome_Etapa': DEFAULT_ETAPAS, 'Ordem': [i for i in range(len(DEFAULT_ETAPAS))]})
        }
        os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)
        with pd.ExcelWriter(config.DATABASE_PATH, engine='openpyxl') as writer:
            for name, df in dfs.items(): df.to_excel(writer, sheet_name=name, index=False)
        _sync_to_drive_async()
        return dfs

    try:
        with excel_lock:
            dfs = pd.read_excel(config.DATABASE_PATH, sheet_name=None)
            
            # 1. Garantir colunas esperadas nos Leads
            if 'Leads' in dfs:
                for col in expected_lead_columns:
                    if col not in dfs['Leads'].columns: dfs['Leads'][col] = ""
            
            # 2. Garantir colunas esperadas no Histórico (Evita KeyError: 'Tipo')
            expected_hist_columns = ['ID_Historico', 'ID_Lead', 'Timestamp', 'Usuario', 'Tipo', 'Campo', 'Antigo', 'Novo', 'Mensagem']
            if 'Historico' in dfs:
                for col in expected_hist_columns:
                    if col not in dfs['Historico'].columns: dfs['Historico'][col] = ""
            
            # 3. Garantir existência de todas as abas
            required_sheets = ['Usuarios', 'Leads', 'Historico', 'Anexos', 'Logs', 'PasswordResetTokens', 'KanbanConfig']
            for sheet in required_sheets:
                if sheet not in dfs:
                    if sheet == 'Logs':
                        dfs[sheet] = pd.DataFrame({'Timestamp': [], 'Nivel': [], 'Mensagem': []})
                    elif sheet == 'PasswordResetTokens':
                        dfs[sheet] = pd.DataFrame({'Token': [], 'Email': [], 'ExpiresAt': [], 'Used': []})
                    else:
                        dfs[sheet] = pd.DataFrame()
            return dfs
    except Exception: return None

def init_session_state():
    if 'db_dfs' not in st.session_state:
        st.session_state.db_dfs = _load_database_from_file()

def get_session_dfs():
    init_session_state()
    return st.session_state.db_dfs

def commit_to_file():
    """Salva localmente e sincroniza com o Google Drive."""
    dfs = get_session_dfs()
    try:
        with excel_lock:
            with pd.ExcelWriter(config.DATABASE_PATH, engine='openpyxl') as writer:
                for name, df in dfs.items(): df.to_excel(writer, sheet_name=name, index=False)
        _sync_to_drive_async()
        st.toast("💾 Dados Sincronizados!", icon="✅")
    except Exception as e: st.error(f"Erro ao salvar: {e}")

# --- Funções de Negócio ---

def get_detailed_leads(sort_order="Mais Recentes"):
    leads = get_all('Leads')
    if leads.empty: return leads
    
    # Ordenação
    leads['Data_Criacao'] = pd.to_datetime(leads['Data_Criacao'])
    if sort_order == "Mais Recentes":
        leads = leads.sort_values('Data_Criacao', ascending=False)
    else:
        leads = leads.sort_values('Data_Criacao', ascending=True)
        
    # Último comentário
    hist = get_all('Historico')
    if not hist.empty and 'Tipo' in hist.columns:
        comms = hist[hist['Tipo'] == 'Comentário'].sort_values('Timestamp', ascending=False)
        last_comm = comms.drop_duplicates('ID_Lead').set_index('ID_Lead')['Mensagem']
        leads['Ultimo_Comentario'] = leads['ID_Lead'].map(last_comm).fillna("Sem notas")
    else:
        leads['Ultimo_Comentario'] = "Sem notas"
    return leads

def get_all(name):
    return get_session_dfs().get(name, pd.DataFrame()).copy()

def get_kanban_stages():
    return DEFAULT_ETAPAS

def create_lead(data, user):
    dfs = get_session_dfs()
    df = dfs['Leads']
    new_id = (df['ID_Lead'].max() + 1) if not df.empty else 1
    now = datetime.now()
    
    new_row = {
        'ID_Lead': new_id, 'Razao_Social': data['Razao_Social'], 'Telefone': data['Telefone'],
        'Nome_Contato': data['Nome_Contato'], 'CNPJ': data['CNPJ'], 'Email': data.get('Email', ''),
        'Etapa_Atual': 'Leads', 'Status': 'Em dia', 'Prioridade': 'Média', 'Nucleo': 'Comercial',
        'Data_Criacao': now, 'Ultima_Atualizacao': now, 'Data_Entrada_Etapa': now,
        'Descricao': '', 'Checklist': '[]'
    }
    dfs['Leads'] = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _add_history(dfs, new_id, "Sistema", "Criação", "", "", "Lead cadastrado no sistema")
    commit_to_file()
    return new_id

def update_lead(lead_id, updates, user, comment="", is_comment=False):
    dfs = get_session_dfs()
    df = dfs['Leads']
    idx = df.index[df['ID_Lead'] == lead_id].tolist()
    if not idx: return False
    i = idx[0]
    
    tipo = "Comentário" if is_comment else "Ação"
    
    for field, val in updates.items():
        if field in df.columns:
            antigo = df.at[i, field]
            _add_history(dfs, lead_id, user['Nome'], tipo, field, antigo, val, comment)
            df.at[i, field] = val
            
    df.at[i, 'Ultima_Atualizacao'] = datetime.now()
    commit_to_file()
    return True

def _add_history(dfs, lead_id, usuario, tipo, campo, antigo, novo, mensagem):
    hist_df = dfs['Historico']
    new_id = (hist_df['ID_Historico'].max() + 1) if not hist_df.empty else 1
    new_entry = pd.DataFrame([{
        'ID_Historico': new_id, 'ID_Lead': lead_id, 'Timestamp': datetime.now(), 
        'Usuario': usuario, 'Tipo': tipo, 'Campo': campo, 
        'Antigo': str(antigo), 'Novo': str(novo), 'Mensagem': mensagem
    }])
    dfs['Historico'] = pd.concat([hist_df, new_entry], ignore_index=True)

def delete_leads(ids, user):
    dfs = get_session_dfs()
    dfs['Leads'] = dfs['Leads'][~dfs['Leads']['ID_Lead'].isin(ids)]
    if 'Historico' in dfs: dfs['Historico'] = dfs['Historico'][~dfs['Historico']['ID_Lead'].isin(ids)]
    commit_to_file()
    return True

def get_user_by_email(email):
    df = get_all('Usuarios')
    if df.empty: return None
    user = df[df['Email'].str.lower() == email.lower()]
    return user.to_dict('records')[0] if not user.empty else None

def user_exists(email):
    df = get_all('Usuarios')
    return not df.empty and not df[df['Email'].str.lower() == email.lower()].empty

def register_user(name, email, pwd, profile):
    dfs = get_session_dfs()
    df = dfs['Usuarios']
    new_id = (df['ID_Usuario'].max() + 1) if not df.empty else 1
    new_row = {'ID_Usuario': new_id, 'Nome': name, 'Email': email, 'Senha': pwd, 'Perfil': profile, 'Ativo': True}
    dfs['Usuarios'] = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    commit_to_file()
    return new_id

def log_system_event(mensagem, nivel="INFO"):
    """Registra um evento de log no banco de dados Excel."""
    dfs = get_session_dfs()
    if 'Logs' not in dfs:
        dfs['Logs'] = pd.DataFrame(columns=['Timestamp', 'Nivel', 'Mensagem'])
    new_log = pd.DataFrame([{'Timestamp': datetime.now(), 'Nivel': nivel, 'Mensagem': mensagem}])
    dfs['Logs'] = pd.concat([dfs['Logs'], new_log], ignore_index=True)
    # Não chamamos commit aqui para evitar loop infinito se chamado em funções de commit

def add_comment_to_lead_history(lead_id, user, comment):
    dfs = get_session_dfs()
    _add_history(dfs, lead_id, user['Nome'], "Comentário", "N/A", "N/A", "N/A", comment)
    commit_to_file()
    return True

def create_anexo_record(tipo_referencia, id_referencia, nome_arquivo, tipo_arquivo, link_drive, usuario_envio, observacao):
    dfs = get_session_dfs()
    df = dfs['Anexos']
    new_id = (df['ID_Anexo'].max() + 1) if not df.empty else 1
    new_row = {
        'ID_Anexo': new_id, 'Tipo_Referencia': tipo_referencia, 'ID_Referencia': id_referencia,
        'Nome_Arquivo': nome_arquivo, 'Link_Drive': link_drive,
        'Usuario_Envio': usuario_envio, 'Data_Envio': datetime.now()
    }
    dfs['Anexos'] = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    if tipo_referencia == "Lead":
        _add_history(dfs, id_referencia, usuario_envio, "Ação", "Anexo", "N/A", nome_arquivo, f"Arquivo '{nome_arquivo}' anexado.")
    commit_to_file()
    return new_id

def get_anexos_by_referencia(tipo, rid):
    df = get_all('Anexos')
    if df.empty: return pd.DataFrame()
    return df[(df['Tipo_Referencia'] == tipo) & (df['ID_Referencia'] == rid)]

def rename_kanban_stage(o, n): return False
def remove_kanban_stage(n): return False
def add_kanban_stage(n, o=0): return False

def create_password_reset_token(email):
    token = secrets.token_urlsafe(32)
    dfs = get_session_dfs()
    tokens_df = dfs.get('PasswordResetTokens', pd.DataFrame())
    expires_at = datetime.now() + timedelta(hours=1)
    new_token = pd.DataFrame([{'Token': token, 'Email': email, 'ExpiresAt': expires_at, 'Used': False}])
    dfs['PasswordResetTokens'] = pd.concat([tokens_df, new_token], ignore_index=True)
    commit_to_file()
    return token

def get_password_reset_token(token):
    dfs = get_session_dfs()
    tokens_df = dfs.get('PasswordResetTokens', pd.DataFrame())
    if tokens_df.empty: return None
    match = tokens_df[(tokens_df['Token'] == token) & (tokens_df['Used'] == False)]
    return match.to_dict('records')[0] if not match.empty else None

def update_user_password(email, pwd):
    dfs = get_session_dfs()
    df = dfs['Usuarios']
    idx = df.index[df['Email'].str.lower() == email.lower()].tolist()
    if not idx: return False
    df.at[idx[0], 'Senha'] = pwd
    commit_to_file()
    return True

def invalidate_password_reset_token(token):
    dfs = get_session_dfs()
    df = dfs['PasswordResetTokens']
    df.loc[df['Token'] == token, 'Used'] = True
    commit_to_file()
    return True
