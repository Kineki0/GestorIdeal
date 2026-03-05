# repository_excel.py
import pandas as pd
import os
import io
import streamlit as st
import openpyxl
import config
import threading
from threading import Lock
from datetime import datetime, timedelta
from config import ETAPAS_KANBAN as DEFAULT_ETAPAS
import utils
import secrets
from googleapiclient.http import MediaIoBaseDownload

# Lock para evitar que dois processos mexam no arquivo ao mesmo tempo
excel_lock = Lock()

# --- Sistema de Sincronização em Segundo Plano (Background Sync) ---

def _sync_worker():
    """Tarefa que roda em segundo plano para subir o arquivo para o Drive sem travar o app."""
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
    """Dispara a sincronização para o Drive em uma thread separada (Não bloqueia o app)."""
    thread = threading.Thread(target=_sync_worker)
    thread.start()

def _sync_from_drive():
    """Baixa o database.xlsx (Bloqueante, usado apenas no início para garantir dados frescos)."""
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

# --- Funções de Carga e Salvamento Otimizadas ---

def _load_database_from_file():
    """Carrega o banco de dados. Tenta o Drive apenas se a sessão estiver vazia."""
    # Se já temos o arquivo local recente, evitamos o download pesado
    if not os.path.exists(config.DATABASE_PATH):
        _sync_from_drive()

    if not os.path.exists(config.DATABASE_PATH):
        # Estrutura inicial (se for a primeira vez absoluta)
        dfs = {
            'Usuarios': pd.DataFrame({'ID_Usuario': [], 'Nome': [], 'Email': [], 'Senha': [], 'Perfil': [], 'Ativo': []}),
            'Leads': pd.DataFrame({
                'ID_Lead': [], 'Descricao': [], 'Nome_Contato': [], 'CNPJ': [], 'Email': [], 
                'Razao_Social': [], 'Nome_Fantasia': [], 'Industria': [], 'Etapa_Atual': [], 
                'Status': [], 'Tags': [], 'Prioridade': [], 'Ultima_Atualizacao': [], 
                'Data_Criacao': [], 'Prazo': [], 'Data_Entrada_Etapa': []
            }),
            'Historico': pd.DataFrame({'ID_Historico': [], 'ID_Lead': [], 'Timestamp': [], 'Usuario': [], 'Campo_Alterado': [], 'Valor_Antigo': [], 'Valor_Novo': [], 'Comentario': []}),
            'Anexos': pd.DataFrame({'ID_Anexo': [], 'Tipo_Referencia': [], 'ID_Referencia': [], 'Nome_Arquivo': [], 'Link_Drive': [], 'Usuario_Envio': [], 'Data_Envio': []}),
            'KanbanConfig': pd.DataFrame({'ID_Etapa': [], 'Nome_Etapa': [], 'Ordem': []})
        }
        os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)
        with pd.ExcelWriter(config.DATABASE_PATH, engine='openpyxl') as writer:
            for name, df in dfs.items(): df.to_excel(writer, sheet_name=name, index=False)
        _sync_to_drive_async()
        return dfs

    try:
        with excel_lock:
            return pd.read_excel(config.DATABASE_PATH, sheet_name=None)
    except Exception: return None

def init_session_state():
    if 'db_dfs' not in st.session_state:
        st.session_state.db_dfs = _load_database_from_file()

def get_session_dfs():
    init_session_state()
    return st.session_state.db_dfs

def commit_to_file():
    """Salva no disco local (Rápido) e sobe para o Drive em segundo plano (Assíncrono)."""
    dfs = get_session_dfs()
    try:
        with excel_lock:
            with pd.ExcelWriter(config.DATABASE_PATH, engine='openpyxl') as writer:
                for name, df in dfs.items():
                    df.to_excel(writer, sheet_name=name, index=False)
        
        # Sobe para o Drive sem travar a tela do usuário
        _sync_to_drive_async()
        st.toast("💾 Alterações persistidas!", icon="🚀")
    except Exception as e:
        st.error(f"Erro ao salvar localmente: {e}")

# --- Funções de Negócio ---

def get_detailed_leads():
    leads = get_all('Leads')
    stages = get_kanban_stages()
    if not leads.empty and 'Etapa_Atual' in leads.columns:
        leads = leads[leads['Etapa_Atual'].isin(stages)]
    
    # Adiciona o último comentário de forma ultra-rápida
    hist = get_all('Historico')
    if not hist.empty:
        comms = hist[hist['Campo_Alterado'] == 'Comentário'].sort_values('Timestamp', ascending=False)
        last_comm = comms.drop_duplicates('ID_Lead').set_index('ID_Lead')['Comentario']
        leads['Ultimo_Comentario'] = leads['ID_Lead'].map(last_comm).fillna("Sem notas")
    else:
        leads['Ultimo_Comentario'] = "Sem notas"
    return leads

def get_all(name):
    dfs = get_session_dfs()
    return dfs.get(name, pd.DataFrame()).copy()

def get_kanban_stages():
    dfs = get_session_dfs()
    kc = dfs.get('KanbanConfig', pd.DataFrame())
    if kc.empty:
        kc = pd.DataFrame([{'ID_Etapa': i+1, 'Nome_Etapa': e, 'Ordem': i} for i, e in enumerate(DEFAULT_ETAPAS)])
        dfs['KanbanConfig'] = kc
    return kc.sort_values('Ordem')['Nome_Etapa'].tolist()

def create_lead(data, user):
    dfs = get_session_dfs()
    df = dfs['Leads']
    new_id = (df['ID_Lead'].max() + 1) if not df.empty else 1
    now = datetime.now()
    etapa = data.get('etapa_inicial', get_kanban_stages()[0])
    
    new_row = {
        'ID_Lead': new_id, 'Descricao': data.get('Descricao'), 'Nome_Contato': data.get('Nome_Contato'),
        'CNPJ': data.get('CNPJ'), 'Email': data.get('Email'), 'Razao_Social': data.get('Razao_Social'),
        'Nome_Fantasia': data.get('Nome_Fantasia'), 'Industria': data.get('Industria', ''),
        'Etapa_Atual': etapa, 'Status': "Em dia", 'Tags': data.get('Tags', ''),
        'Prioridade': data.get('Prioridade', 'Média'), 'Ultima_Atualizacao': now,
        'Data_Criacao': now, 'Prazo': data.get('Prazo'), 'Data_Entrada_Etapa': now
    }
    dfs['Leads'] = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _add_history(dfs, new_id, "Lead", "N/A", "Criado", user['Nome'], "Lead inicializado")
    commit_to_file()
    return new_id

def update_lead(lead_id, updates, user, comment=""):
    dfs = get_session_dfs()
    df = dfs['Leads']
    idx = df.index[df['ID_Lead'] == lead_id].tolist()
    if not idx: return False
    i = idx[0]
    
    if 'Etapa_Atual' in updates and updates['Etapa_Atual'] != df.at[i, 'Etapa_Atual']:
        updates['Data_Entrada_Etapa'] = datetime.now()

    for field, val in updates.items():
        _add_history(dfs, lead_id, field, df.at[i, field], val, user['Nome'], comment)
        df.at[i, field] = val
    df.at[i, 'Ultima_Atualizacao'] = datetime.now()
    commit_to_file()
    return True

def add_comment_to_lead_history(lead_id, user, comment):
    dfs = get_session_dfs()
    _add_history(dfs, lead_id, "Comentário", "N/A", comment, user['Nome'], comment)
    commit_to_file()
    return True

def _add_history(dfs, lead_id, field, old_val, new_val, user_name, comment=""):
    hist_df = dfs['Historico']
    new_id = (hist_df['ID_Historico'].max() + 1) if not hist_df.empty else 1
    new_entry = pd.DataFrame([{
        'ID_Historico': new_id, 'ID_Lead': lead_id, 'Timestamp': datetime.now(), 
        'Usuario': user_name, 'Campo_Alterado': field, 'Valor_Antigo': str(old_val), 
        'Valor_Novo': str(new_val), 'Comentario': comment
    }])
    dfs['Historico'] = pd.concat([hist_df, new_entry], ignore_index=True)

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
    _add_history(dfs, id_referencia, "Anexo", "N/A", nome_arquivo, usuario_envio, f"Arquivo '{nome_arquivo}' anexado.")
    commit_to_file()
    return new_id

def get_anexos_by_referencia(tipo, rid):
    df = get_all('Anexos')
    if df.empty: return pd.DataFrame()
    return df[(df['Tipo_Referencia'] == tipo) & (df['ID_Referencia'] == rid)]

def rename_kanban_stage(old, new):
    dfs = get_session_dfs()
    dfs['KanbanConfig'].loc[dfs['KanbanConfig']['Nome_Etapa'] == old, 'Nome_Etapa'] = new
    dfs['Leads'].loc[dfs['Leads']['Etapa_Atual'] == old, 'Etapa_Atual'] = new
    commit_to_file()
    return True

def remove_kanban_stage(name):
    dfs = get_session_dfs()
    dfs['KanbanConfig'] = dfs['KanbanConfig'][dfs['KanbanConfig']['Nome_Etapa'] != name]
    commit_to_file()
    return True

def add_kanban_stage(name, order=0):
    dfs = get_session_dfs()
    kc = dfs['KanbanConfig']
    new_id = (kc['ID_Etapa'].max() + 1) if not kc.empty else 1
    new_row = {'ID_Etapa': new_id, 'Nome_Etapa': name, 'Ordem': order}
    dfs['KanbanConfig'] = pd.concat([kc, pd.DataFrame([new_row])], ignore_index=True).sort_values('Ordem')
    commit_to_file()
    return True

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

def log_system_event(msg, level="INFO"): pass
