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
from config import ETAPAS_KANBAN as DEFAULT_ETAPAS, CHECKLIST_PADRAO
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
        
        # 1. Localiza o banco principal
        query = f"name='database.xlsx' and '{root_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields="files(id, modifiedTime)").execute()
        files = results.get('files', [])
        
        if not os.path.exists(config.DATABASE_PATH): return
        with open(config.DATABASE_PATH, 'rb') as f: content = f.read()
        
        class MockFile:
            def __init__(self, c): self.c = c
            def getvalue(self): return self.c
            @property
            def type(self): return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            @property
            def name(self): return "database.xlsx"
            
        mock = MockFile(content)
        
        # 2. Sincroniza o arquivo principal
        if files:
            drive_manager.update_file(files[0]['id'], mock)
        else:
            drive_manager.upload_file(mock, "database.xlsx", root_id)
            
        # 3. LÓGICA DE BACKUP DIÁRIO (Snapshot)
        # Verifica se o último backup na pasta de backups foi hoje
        backups_folder_id = drive_manager.find_or_create_folder("Backups", root_id)
        last_backup_query = f"'{backups_folder_id}' in parents and trashed=false"
        last_backups = service.files().list(q=last_backup_query, orderBy="createdTime desc", pageSize=1, fields="files(name, createdTime)").execute()
        
        today_str = datetime.now().strftime("%Y%m%d")
        needs_backup = True
        if last_backups.get('files'):
            last_date = last_backups['files'][0]['name']
            if today_str in last_date: needs_backup = False
            
        if needs_backup:
            drive_manager.create_backup_snapshot(mock)
            
    except Exception: pass

def _sync_to_drive_async():
    threading.Thread(target=_sync_worker).start()

# --- Funções de Leitura e Escrita Otimizadas ---

@st.cache_data(ttl=600) # Cache de 10 minutos para leitura do disco
def _read_excel_file(path):
    """Lê o arquivo Excel com cache do Streamlit."""
    try:
        with excel_lock:
            return pd.read_excel(path, sheet_name=None)
    except Exception:
        return None

def _load_database_from_file():
    # Sincroniza do drive apenas na inicialização fria
    if 'db_last_sync' not in st.session_state:
        _sync_from_drive()
        st.session_state.db_last_sync = datetime.now()

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
            'KanbanConfig': pd.DataFrame({'ID_Etapa': [i+1 for i in range(len(DEFAULT_ETAPAS))], 'Nome_Etapa': DEFAULT_ETAPAS, 'Ordem': [i for i in range(len(DEFAULT_ETAPAS))]}),
            'Jarvis_Brain': pd.DataFrame({'ID_Conhecimento': [], 'Palavra_Chave': [], 'Resposta': [], 'Status': [], 'Usuario_Sugeriu': [], 'Data_Criacao': []})
        }
        os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)
        with pd.ExcelWriter(config.DATABASE_PATH, engine='openpyxl') as writer:
            for name, df in dfs.items(): df.to_excel(writer, sheet_name=name, index=False)
        _sync_to_drive_async()
        return dfs

    # Tenta ler do cache de arquivo primeiro
    dfs = _read_excel_file(config.DATABASE_PATH)
    
    if dfs:
        # Garantir existência de todas as abas
        required_sheets = ['Usuarios', 'Leads', 'Historico', 'Anexos', 'Logs', 'PasswordResetTokens', 'KanbanConfig', 'Jarvis_Brain']
        for sheet in required_sheets:
            if sheet not in dfs:
                if sheet == 'Jarvis_Brain':
                    dfs[sheet] = pd.DataFrame({'ID_Conhecimento': [], 'Palavra_Chave': [], 'Resposta': [], 'Status': [], 'Usuario_Sugeriu': [], 'Data_Criacao': []})
                elif sheet == 'Logs':
                    dfs[sheet] = pd.DataFrame({'Timestamp': [], 'Nivel': [], 'Mensagem': []})
                else:
                    dfs[sheet] = pd.DataFrame()
        return dfs
    return None

def init_session_state():
    if 'db_dfs' not in st.session_state:
        st.session_state.db_dfs = _load_database_from_file()

def get_session_dfs():
    init_session_state()
    return st.session_state.db_dfs

def commit_to_file():
    """Salva localmente (instantâneo) e agenda sincronização em background."""
    dfs = get_session_dfs()
    try:
        # 1. Salva no arquivo local IMEDIATAMENTE (rápido)
        with excel_lock:
            with pd.ExcelWriter(config.DATABASE_PATH, engine='openpyxl') as writer:
                for name, df in dfs.items(): df.to_excel(writer, sheet_name=name, index=False)
        
        # 2. Dispara a sincronização com o Drive em SEGUNDO PLANO (não trava o usuário)
        _sync_to_drive_async()
        
        # 3. Limpa o cache de leitura APÓS agendar o sync
        # Isso garante que a próxima leitura de QUALQUER thread recarregue os novos dados.
        st.cache_data.clear()
        
        st.toast("💾 Alterações salvas!", icon="✅")
    except Exception as e: 
        st.error(f"Erro ao salvar: {e}")

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
    
    # --- ADICIONA TAREFAS PADRÃO DA ETAPA INICIAL (Leads) ---
    initial_tasks = [{"task": t, "done": False} for t in CHECKLIST_PADRAO.get('Leads', [])]
    
    new_row = {
        'ID_Lead': new_id, 'Razao_Social': data['Razao_Social'], 'Telefone': data['Telefone'],
        'Nome_Contato': data['Nome_Contato'], 'CNPJ': data['CNPJ'], 'Email': data.get('Email', ''),
        'Etapa_Atual': 'Leads', 'Status': 'Em dia', 'Prioridade': 'Média', 'Nucleo': 'Comercial',
        'Data_Criacao': now, 'Ultima_Atualizacao': now, 'Data_Entrada_Etapa': now,
        'Descricao': '', 'Checklist': json.dumps(initial_tasks)
    }
    dfs['Leads'] = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    _add_history(dfs, new_id, "Sistema", "Ação", "Lead", "N/A", "Criado", "Lead cadastrado no sistema")
    commit_to_file()

    # --- Automação Google Drive (Criação de Pastas) ---
    try:
        from services import drive_manager
        if drive_manager.check_drive_connection():
            drive_manager.setup_lead_folders(data['Razao_Social'])
    except Exception: pass

    return new_id

def update_lead(lead_id, updates, user, comment="", is_comment=False):
    dfs = get_session_dfs()
    df = dfs['Leads']
    idx = df.index[df['ID_Lead'] == lead_id].tolist()
    if not idx: return False
    i = idx[0]
    
    tipo = "Comentário" if is_comment else "Ação"
    
    # --- LÓGICA DE AUTOMATIZAÇÃO DE CHECKLIST POR ETAPA ---
    if 'Etapa_Atual' in updates:
        nova_etapa = updates['Etapa_Atual']
        if nova_etapa != df.at[i, 'Etapa_Atual']:
            # Carrega checklist atual
            try:
                current_checklist = json.loads(df.at[i, 'Checklist']) if df.at[i, 'Checklist'] else []
            except:
                current_checklist = []
            
            # Pega nomes das tarefas que já existem
            existing_task_names = [t['task'] for t in current_checklist]
            
            # Adiciona apenas tarefas que NÃO existem ainda
            new_tasks = CHECKLIST_PADRAO.get(nova_etapa, [])
            for nt in new_tasks:
                if nt not in existing_task_names:
                    current_checklist.append({"task": nt, "done": False})
            
            df.at[i, 'Checklist'] = json.dumps(current_checklist)
            df.at[i, 'Data_Entrada_Etapa'] = datetime.now()
    
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

def delete_anexo(anexo_id):
    """Remove um registro de anexo do Excel."""
    dfs = get_session_dfs()
    if 'Anexos' in dfs:
        dfs['Anexos'] = dfs['Anexos'][dfs['Anexos']['ID_Anexo'] != anexo_id]
        commit_to_file()
        return True
    return False

def delete_lead(lead_id):
    """Remove um lead, seu histórico e seus anexos do banco de dados."""
    dfs = get_session_dfs()
    
    # Remove o lead
    if 'Leads' in dfs:
        dfs['Leads'] = dfs['Leads'][dfs['Leads']['ID_Lead'] != lead_id]
        
    # Remove o histórico vinculado
    if 'Historico' in dfs:
        dfs['Historico'] = dfs['Historico'][dfs['Historico']['ID_Lead'] != lead_id]
        
    # Remove os registros de anexos vinculados
    if 'Anexos' in dfs:
        dfs['Anexos'] = dfs['Anexos'][(dfs['Anexos']['Tipo_Referencia'] != 'Lead') | (dfs['Anexos']['ID_Referencia'] != lead_id)]
        
    commit_to_file()
    return True

def delete_leads_by_stage(stage_name):
    """Remove todos os leads de uma etapa específica, incluindo histórico e anexos."""
    dfs = get_session_dfs()
    if 'Leads' not in dfs or dfs['Leads'].empty: return False
    
    # 1. Identifica IDs dos leads nesta etapa
    leads_to_remove = dfs['Leads'][dfs['Leads']['Etapa_Atual'] == stage_name]['ID_Lead'].tolist()
    if not leads_to_remove: return False
    
    # 2. Remove os leads
    dfs['Leads'] = dfs['Leads'][dfs['Leads']['Etapa_Atual'] != stage_name]
    
    # 3. Remove histórico vinculado
    if 'Historico' in dfs:
        dfs['Historico'] = dfs['Historico'][~dfs['Historico']['ID_Lead'].isin(leads_to_remove)]
        
    # 4. Remove anexos vinculados
    if 'Anexos' in dfs:
        dfs['Anexos'] = dfs['Anexos'][~((dfs['Anexos']['Tipo_Referencia'] == 'Lead') & (dfs['Anexos']['ID_Referencia'].isin(leads_to_remove)))]
    
    commit_to_file()
    return True

def sync_kanban_stages(edited_df):
    """Sincroniza as etapas do Kanban com as edições feitas no admin."""
    dfs = get_session_dfs()
    # Garante que a coluna 'Ordem' seja preenchida se houver novos registros
    edited_df = edited_df.reset_index(drop=True)
    edited_df['Ordem'] = edited_df.index

    # Gera novos IDs se necessário (registros com ID_Etapa vazio)
    max_id = edited_df['ID_Etapa'].max() if not edited_df['ID_Etapa'].empty else 0
    for idx, row in edited_df.iterrows():
        if pd.isna(row['ID_Etapa']):
            max_id += 1
            edited_df.at[idx, 'ID_Etapa'] = max_id

    dfs['KanbanConfig'] = edited_df
    commit_to_file()
    return True

def get_kanban_stages():
    """Retorna a lista de nomes das etapas do Kanban na ordem correta."""
    dfs = get_session_dfs()
    df = dfs.get('KanbanConfig', pd.DataFrame())
    if df.empty:
        return config.ETAPAS_KANBAN
    return df.sort_values('Ordem')['Nome_Etapa'].tolist()

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

# --- FUNÇÕES DO CÉREBRO DO JARVIS ---

def suggest_knowledge(palavra_chave, resposta, usuario):
    """Registra uma sugestão de conhecimento para aprovação posterior."""
    dfs = get_session_dfs()
    df = dfs['Jarvis_Brain']
    new_id = (df['ID_Conhecimento'].max() + 1) if not df.empty else 1
    new_row = {
        'ID_Conhecimento': new_id, 
        'Palavra_Chave': palavra_chave.lower().strip(), 
        'Resposta': resposta, 
        'Status': 'Pendente', 
        'Usuario_Sugeriu': usuario, 
        'Data_Criacao': datetime.now()
    }
    dfs['Jarvis_Brain'] = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    commit_to_file()
    return True

def get_active_knowledge():
    """Retorna todo o conhecimento aprovado em formato de dicionário."""
    df = get_all('Jarvis_Brain')
    if df.empty: return {}
    approved = df[df['Status'] == 'Aprovado']
    return dict(zip(approved['Palavra_Chave'], approved['Resposta']))

def sync_knowledge_base(edited_df):
    """Sincroniza o cérebro do Jarvis com as edições do Admin."""
    dfs = get_session_dfs()
    dfs['Jarvis_Brain'] = edited_df
    commit_to_file()
    return True
