# repository_excel.py
import pandas as pd
import os
import streamlit as st
import openpyxl
import config
from datetime import datetime, timedelta
from config import ETAPAS_KANBAN as DEFAULT_ETAPAS
import utils
import secrets

# Lock to prevent race conditions when writing to Excel
from threading import Lock
excel_lock = Lock()

# --- Funções de Leitura e Escrita (Otimizadas com Session State) ---

@st.cache_data(ttl=300) # Cache para a leitura inicial do arquivo
def _load_database_from_file():
    """
    Carrega o arquivo Excel do disco. Esta é a operação lenta que queremos minimizar.
    Retorna um dicionário de DataFrames.
    """
    if not os.path.exists(config.DATABASE_PATH):
        # Estrutura inicial se o arquivo não existir
        dfs = {
            'Clientes': pd.DataFrame({'ID_Cliente': [], 'Nome_Cliente': [], 'Ativo': []}),
            'Servicos': pd.DataFrame({'ID_Servico': [], 'Nome_Servico': [], 'Ativo': []}),
            'Usuarios': pd.DataFrame({'ID_Usuario': [], 'Nome': [], 'Email': [], 'Senha': [], 'Perfil': [], 'Ativo': []}),
            'Leads': pd.DataFrame({
                'ID_Lead': [], 'Descricao': [], 'Nome_Contato': [], 'CNPJ': [], 'CNPJ2': [],
                'Email': [], 'Contato1': [], 'Contato2': [], 'Razao_Social': [],
                'Nome_Fantasia': [], 'Razao_Social2': [], 'Nome_Fantasia2': [],
                'Industria': [], 'Etapa_Atual': [], 'Status': [], 'Tags': [],
                'Prioridade': [], 'Ultima_Atualizacao': [], 'Data_Criacao': [], 'Prazo': [],
                'Data_Entrada_Etapa': []
            }),
            'Historico': pd.DataFrame({'ID_Historico': [], 'ID_Lead': [], 'Timestamp': [], 'Usuario': [], 'Campo_Alterado': [], 'Valor_Antigo': [], 'Valor_Novo': [], 'Comentario': []}),
            'Logs': pd.DataFrame({'Timestamp': [], 'Nivel': [], 'Mensagem': []}),
            'PasswordResetTokens': pd.DataFrame({'Token': [], 'Email': [], 'ExpiresAt': [], 'Used': []}),
            'Anexos': pd.DataFrame({'ID_Anexo': [], 'Tipo_Referencia': [], 'ID_Referencia': [], 'Nome_Arquivo': [], 'Tipo_Arquivo': [], 'Link_Drive': [], 'Usuario_Envio': [], 'Data_Envio': [], 'Observacao': []}),
            'KanbanConfig': pd.DataFrame({'ID_Etapa': [], 'Nome_Etapa': [], 'Ordem': []})
        }
        # Salva o arquivo inicial e retorna os dfs
        commit_to_file(dfs)
        return dfs

    try:
        with excel_lock:
            dfs = pd.read_excel(config.DATABASE_PATH, sheet_name=None)
        
        expected_lead_columns = [
            'ID_Lead', 'Descricao', 'Nome_Contato', 'CNPJ', 'CNPJ2',
            'Email', 'Contato1', 'Contato2', 'Razao_Social',
            'Nome_Fantasia', 'Razao_Social2', 'Nome_Fantasia2',
            'Industria', 'Etapa_Atual', 'Status', 'Tags',
            'Prioridade', 'Ultima_Atualizacao', 'Data_Criacao', 'Prazo',
            'Data_Entrada_Etapa'
        ]

        if 'Leads' not in dfs:
            dfs['Leads'] = pd.DataFrame(columns=expected_lead_columns)
        else:
            for col in expected_lead_columns:
                if col not in dfs['Leads'].columns:
                    if col == 'Etapa_Atual':
                        dfs['Leads'][col] = DEFAULT_ETAPAS[0] if DEFAULT_ETAPAS else ""
                    elif col == 'Prioridade':
                        dfs['Leads'][col] = "Média"
                    elif col == 'Status':
                        dfs['Leads'][col] = "Em dia"
                    elif col in ['Ultima_Atualizacao', 'Data_Criacao', 'Prazo']:
                        dfs['Leads'][col] = pd.NaT
                    else:
                        dfs['Leads'][col] = ''
        
        if 'KanbanConfig' not in dfs:
            dfs['KanbanConfig'] = pd.DataFrame({'ID_Etapa': [], 'Nome_Etapa': [], 'Ordem': []})

        for name, df in dfs.items():
            for col in df.columns:
                if 'data' in col.lower() or 'prazo' in col.lower() or 'timestamp' in col.lower():
                    dfs[name][col] = pd.to_datetime(dfs[name][col], errors='coerce')
        return dfs
    except Exception as e:
        st.error(f"Erro Crítico ao carregar Excel: {e}")
        return None

def init_session_state():
    """
    Inicializa o banco de dados no st.session_state se ainda não estiver lá.
    """
    if 'db_dfs' not in st.session_state:
        st.session_state.db_dfs = _load_database_from_file()

def get_session_dfs():
    """
    Retorna o dicionário de DataFrames do st.session_state.
    Garante que o estado da sessão seja inicializado.
    """
    init_session_state()
    return st.session_state.db_dfs

def commit_to_file():
    """
    Salva o dicionário de DataFrames do session_state para o arquivo Excel.
    """
    dfs_to_save = get_session_dfs()
    try:
        with excel_lock:
            with pd.ExcelWriter(config.DATABASE_PATH, engine='openpyxl') as writer:
                for sheet_name, df in dfs_to_save.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        st.cache_data.clear() # Limpa o cache de leitura após a escrita
        st.toast("Alterações salvas com sucesso no banco de dados!")
    except Exception as e:
        st.error(f"Falha ao salvar os dados no arquivo. Erro: {e}")


def get_all_data():
    return get_session_dfs()

def get_all(sheet_name):
    dfs = get_session_dfs()
    return dfs.get(sheet_name, pd.DataFrame()).copy()

def update_entity(sheet_name, entity_id_col, entity_id, updates):
    dfs = get_session_dfs()
    df = dfs.get(sheet_name)

    if df is None: return False
    if entity_id_col not in df.columns: return False

    try:
        # A conversão de tipo é importante aqui
        entity_id_type = type(entity_id)
        df[entity_id_col] = df[entity_id_col].astype(entity_id_type)
        idx = df.index[df[entity_id_col] == entity_id].tolist()
    except (TypeError, ValueError):
        return False
        
    if not idx: return False
    
    index = idx[0]
    for field, new_value in updates.items():
        if field in df.columns:
            df.at[index, field] = new_value
    return True

def get_kanban_stages():
    dfs = get_session_dfs()
    kanban_config = dfs.get('KanbanConfig', pd.DataFrame())
    
    if kanban_config.empty:
        default_stages = [{'ID_Etapa': i + 1, 'Nome_Etapa': etapa, 'Ordem': i} for i, etapa in enumerate(DEFAULT_ETAPAS)]
        kanban_config = pd.DataFrame(default_stages)
        dfs['KanbanConfig'] = kanban_config
        
    stages = kanban_config.dropna(subset=['Nome_Etapa'])
    stages = stages[stages['Nome_Etapa'] != '']
    return stages.sort_values(by='Ordem')['Nome_Etapa'].tolist()

def add_kanban_stage(stage_name, insert_at_order=None):
    dfs = get_session_dfs()
    kanban_config = dfs.get('KanbanConfig', pd.DataFrame())

    if stage_name in kanban_config['Nome_Etapa'].values: return

    if insert_at_order is None:
        try:
            insert_at_order = kanban_config[kanban_config['Nome_Etapa'] == 'Concluído']['Ordem'].iloc[0]
        except IndexError:
            insert_at_order = kanban_config['Ordem'].max() + 1 if not kanban_config.empty else 0

    # Desloca as ordens existentes para abrir espaço
    kanban_config.loc[kanban_config['Ordem'] >= insert_at_order, 'Ordem'] += 1

    new_id = (kanban_config['ID_Etapa'].max() + 1) if not kanban_config.empty and not kanban_config['ID_Etapa'].isna().all() else 1
    new_stage = pd.DataFrame([{'ID_Etapa': new_id, 'Nome_Etapa': stage_name, 'Ordem': insert_at_order}])
    
    final_df = pd.concat([kanban_config, new_stage], ignore_index=True).sort_values(by='Ordem').reset_index(drop=True)
    final_df['Ordem'] = final_df.index # Re-indexa para garantir integridade
    dfs['KanbanConfig'] = final_df

def delete_leads(lead_ids, user):
    """Remove múltiplos leads do banco de dados e registros relacionados (Histórico, Anexos)."""
    dfs = get_session_dfs()
    ids_to_remove = [int(lid) for lid in lead_ids]
    
    # 1. Remover da tabela Leads
    leads_df = dfs['Leads']
    removed_count = len(leads_df[leads_df['ID_Lead'].isin(ids_to_remove)])
    dfs['Leads'] = leads_df[~leads_df['ID_Lead'].isin(ids_to_remove)].reset_index(drop=True)
    
    # 2. Remover da tabela Historico (Cascading Delete)
    if 'Historico' in dfs:
        hist_df = dfs['Historico']
        dfs['Historico'] = hist_df[~hist_df['ID_Lead'].isin(ids_to_remove)].reset_index(drop=True)
        
    # 3. Remover da tabela Anexos (Cascading Delete)
    if 'Anexos' in dfs:
        anexos_df = dfs['Anexos']
        # Anexos vinculam leads via ID_Referencia quando Tipo_Referencia é 'Lead'
        mask = (anexos_df['Tipo_Referencia'] == 'Lead') & (anexos_df['ID_Referencia'].isin(ids_to_remove))
        dfs['Anexos'] = anexos_df[~mask].reset_index(drop=True)
    
    log_system_event(f"Usuário {user['Nome']} excluiu {removed_count} leads e seus respectivos históricos.", "AVISO")
    return True

def sync_kanban_stages(edited_df):
    dfs = get_session_dfs()
    kanban_config = dfs.get('KanbanConfig', pd.DataFrame())
    edited_df_copy = edited_df.copy().reset_index(drop=True)
    edited_df_copy['Ordem'] = edited_df_copy.index

    new_stages = edited_df_copy[edited_df_copy['ID_Etapa'].isna()]
    existing_stages = edited_df_copy.dropna(subset=['ID_Etapa'])
    
    new_kanban_config_list = []
    max_id = kanban_config['ID_Etapa'].max() if not kanban_config.empty and not kanban_config['ID_Etapa'].isna().all() else 0

    if not existing_stages.empty:
        new_kanban_config_list.extend(existing_stages.to_dict('records'))

    for _, row in new_stages.iterrows():
        max_id += 1
        new_kanban_config_list.append({'ID_Etapa': max_id, 'Nome_Etapa': row['Nome_Etapa'], 'Ordem': row['Ordem']})
        
    final_kanban_df = pd.DataFrame(new_kanban_config_list).sort_values(by='Ordem').reset_index(drop=True)
    final_kanban_df['Ordem'] = final_kanban_df.index
    dfs['KanbanConfig'] = final_kanban_df

def get_user_by_email(email):
    users_df = get_all('Usuarios')
    if users_df.empty: return None
    user = users_df[users_df['Email'].str.lower() == email.lower()]
    return user.to_dict('records')[0] if not user.empty else None

def user_exists(email):
    users_df = get_all('Usuarios')
    return not users_df.empty and not users_df[users_df['Email'].str.lower() == email.lower()].empty

def get_detailed_leads():
    leads = get_all('Leads')
    valid_stages = get_kanban_stages()
    leads = leads[leads['Etapa_Atual'].isin(valid_stages)]
    
    # Adicionar o último comentário ao dataframe de leads
    historico = get_all('Historico')
    if not historico.empty:
        # Filtrar apenas por comentários ou alterações relevantes
        comentarios = historico[historico['Campo_Alterado'] == 'Comentário'].sort_values('Timestamp', ascending=False)
        last_comments = comentarios.drop_duplicates('ID_Lead').set_index('ID_Lead')['Comentario']
        leads['Ultimo_Comentario'] = leads['ID_Lead'].map(last_comments).fillna("Nenhum comentário.")
    else:
        leads['Ultimo_Comentario'] = "Nenhum comentário."
        
    return leads

def _add_history(dfs, lead_id, field, old_value, new_value, user_name, comentario=""):
    historico_df = dfs['Historico']
    new_id = (historico_df['ID_Historico'].max() + 1) if not historico_df.empty else 1
    new_log = pd.DataFrame([{'ID_Historico': new_id, 'ID_Lead': lead_id, 'Timestamp': datetime.now(), 'Usuario': user_name, 'Campo_Alterado': field, 'Valor_Antigo': str(old_value), 'Valor_Novo': str(new_value), 'Comentario': comentario}])
    dfs['Historico'] = pd.concat([historico_df, new_log], ignore_index=True)

def update_lead(lead_id, updates, user, comentario=""):
    dfs = get_session_dfs()
    leads_df = dfs['Leads']
    idx = leads_df.index[leads_df['ID_Lead'] == lead_id].tolist()
    if not idx: return False
    index = idx[0]
    
    # Se a etapa mudou, atualiza a data de entrada para o SLA
    if 'Etapa_Atual' in updates and updates['Etapa_Atual'] != leads_df.at[index, 'Etapa_Atual']:
        updates['Data_Entrada_Etapa'] = datetime.now()

    for field, new_value in updates.items():
        old_value = leads_df.at[index, field]
        _add_history(dfs, lead_id, field, old_value, new_value, user['Nome'], comentario)
        leads_df.at[index, field] = new_value
    leads_df.at[index, 'Ultima_Atualizacao'] = datetime.now()
    if 'Etapa_Atual' in updates:
        leads_df.at[index, 'Status'] = "Em dia" if updates['Etapa_Atual'] not in ['Concluído', 'Cancelado'] else updates['Etapa_Atual']
    return True

def create_lead(lead_data, user, comentario="Lead Criado"):
    dfs = get_session_dfs()
    leads_df = dfs['Leads']
    etapas = get_kanban_stages()
    etapa = lead_data.get('etapa_inicial', etapas[0] if etapas else "")
    new_id = (leads_df['ID_Lead'].max() + 1) if not leads_df.empty else 1
    
    now = datetime.now()
    new_lead_data = {
        'ID_Lead': new_id,
        'Descricao': lead_data.get('Descricao'),
        'Nome_Contato': lead_data.get('Nome_Contato'),
        'CNPJ': lead_data.get('CNPJ'),
        'CNPJ2': lead_data.get('CNPJ2'),
        'Email': lead_data.get('Email'),
        'Contato1': lead_data.get('Contato1'),
        'Contato2': lead_data.get('Contato2'),
        'Razao_Social': lead_data.get('Razao_Social'),
        'Nome_Fantasia': lead_data.get('Nome_Fantasia'),
        'Razao_Social2': lead_data.get('Razao_Social2'),
        'Nome_Fantasia2': lead_data.get('Nome_Fantasia2'),
        'Industria': lead_data.get('Industria'),
        'Etapa_Atual': etapa,
        'Status': "Em dia",
        'Tags': lead_data.get('Tags'),
        'Prioridade': lead_data.get('Prioridade'),
        'Ultima_Atualizacao': now,
        'Data_Criacao': now,
        'Prazo': pd.NaT if lead_data.get('Prazo') is None else lead_data.get('Prazo'),
        'Data_Entrada_Etapa': now
    }
    
    # Alerta por e-mail para urgência
    if lead_data.get('Prioridade') == 'Alta':
        try:
            from services import email_manager
            subj = f"🚨 NOVO LEAD URGENTE: #{new_id} - {lead_data.get('Razao_Social')}"
            msg = f"Um lead de prioridade ALTA foi criado no sistema.\nEmpresa: {lead_data.get('Razao_Social')}\nEtapa: {etapa}\nCriado por: {user['Nome']}"
            email_manager.send_email(user['Email'], subj, msg, is_html=False)
        except: pass

    new_lead = pd.DataFrame([new_lead_data])
    dfs['Leads'] = pd.concat([leads_df, new_lead], ignore_index=True)
    _add_history(dfs, new_id, "Lead", "N/A", "Criado", user['Nome'], comentario)
    return new_id

def add_comment_to_lead_history(lead_id, user, comment):
    dfs = get_session_dfs()
    _add_history(dfs, lead_id, "Comentário", "N/A", comment, user['Nome'], comment)
    return True

def create_anexo_record(tipo_referencia, id_referencia, nome_arquivo, tipo_arquivo, link_drive, usuario_envio, observacao):
    dfs = get_session_dfs()
    anexos_df = dfs.get('Anexos', pd.DataFrame())
    new_id = (anexos_df['ID_Anexo'].max() + 1) if not anexos_df.empty else 1
    new_anexo = pd.DataFrame([{'ID_Anexo': new_id, 'Tipo_Referencia': tipo_referencia, 'ID_Referencia': id_referencia, 'Nome_Arquivo': nome_arquivo, 'Tipo_Arquivo': tipo_arquivo, 'Link_Drive': link_drive, 'Usuario_Envio': usuario_envio, 'Data_Envio': datetime.now(), 'Observacao': observacao}])
    dfs['Anexos'] = pd.concat([anexos_df, new_anexo], ignore_index=True)
    if tipo_referencia == "Lead":
        comentario_hist = f"Anexo '{nome_arquivo}' adicionado."
        _add_history(dfs, id_referencia, "Anexo", "N/A", nome_arquivo, usuario_envio, comentario_hist)
    return new_id

def get_anexos_by_referencia(tipo_referencia, id_referencia):
    anexos_df = get_all('Anexos')
    if anexos_df.empty: return pd.DataFrame()
    return anexos_df[(anexos_df['Tipo_Referencia'] == tipo_referencia) & (anexos_df['ID_Referencia'] == id_referencia)]

def log_system_event(mensagem, nivel="INFO"):
    """
    Registra um evento de log no banco de dados Excel.
    """
    dfs = get_session_dfs()
    logs_df = dfs.get('Logs', pd.DataFrame(columns=['Timestamp', 'Nivel', 'Mensagem']))
    new_log = pd.DataFrame([{'Timestamp': datetime.now(), 'Nivel': nivel, 'Mensagem': mensagem}])
    dfs['Logs'] = pd.concat([logs_df, new_log], ignore_index=True)

def register_user(name, email, hashed_password, profile):
    """
    Cadastra um novo usuário no banco de dados.
    """
    dfs = get_session_dfs()
    users_df = dfs.get('Usuarios', pd.DataFrame())
    new_id = (users_df['ID_Usuario'].max() + 1) if not users_df.empty else 1
    new_user = pd.DataFrame([{
        'ID_Usuario': new_id,
        'Nome': name,
        'Email': email,
        'Senha': hashed_password,
        'Perfil': profile,
        'Ativo': True
    }])
    dfs['Usuarios'] = pd.concat([users_df, new_user], ignore_index=True)
    log_system_event(f"Novo usuário cadastrado: {email}", "INFO")
    return new_id

def create_password_reset_token(email):
    """
    Cria um token de reset de senha para um email.
    """
    import secrets
    token = secrets.token_urlsafe(32)
    dfs = get_session_dfs()
    tokens_df = dfs.get('PasswordResetTokens', pd.DataFrame())
    expires_at = datetime.now() + timedelta(hours=1)
    new_token = pd.DataFrame([{
        'Token': token,
        'Email': email,
        'ExpiresAt': expires_at,
        'Used': False
    }])
    dfs['PasswordResetTokens'] = pd.concat([tokens_df, new_token], ignore_index=True)
    log_system_event(f"Token de reset de senha gerado para: {email}", "INFO")
    return token

def get_password_reset_token(token):
    """
    Retorna o registro de um token de reset de senha se ele for válido.
    """
    dfs = get_session_dfs()
    tokens_df = dfs.get('PasswordResetTokens', pd.DataFrame())
    if tokens_df.empty: return None
    
    # Garantir que a coluna 'Used' seja booleana para comparação
    tokens_df['Used'] = tokens_df['Used'].astype(bool)
    
    match = tokens_df[
        (tokens_df['Token'] == token) & 
        (tokens_df['Used'] == False) & 
        (pd.to_datetime(tokens_df['ExpiresAt']) > datetime.now())
    ]
    return match.to_dict('records')[0] if not match.empty else None

def update_user_password(email, hashed_password):
    """
    Atualiza a senha de um usuário.
    """
    dfs = get_session_dfs()
    users_df = dfs.get('Usuarios', pd.DataFrame())
    if users_df.empty: return False
    
    idx = users_df.index[users_df['Email'].str.lower() == email.lower()].tolist()
    if not idx: return False
    
    users_df.at[idx[0], 'Senha'] = hashed_password
    log_system_event(f"Senha atualizada para o usuário: {email}", "INFO")
    return True

def invalidate_password_reset_token(token):
    """
    Marca um token de reset de senha como utilizado.
    """
    dfs = get_session_dfs()
    tokens_df = dfs.get('PasswordResetTokens', pd.DataFrame())
    if tokens_df.empty: return False
    
    idx = tokens_df.index[tokens_df['Token'] == token].tolist()
    if not idx: return False
    
    tokens_df.at[idx[0], 'Used'] = True
    return True

def rename_kanban_stage(old_name, new_name):
    """Altera o nome de uma etapa no Kanban e atualiza os leads vinculados."""
    dfs = get_session_dfs()
    kanban_config = dfs.get('KanbanConfig', pd.DataFrame())
    leads_df = dfs.get('Leads', pd.DataFrame())
    
    if old_name not in kanban_config['Nome_Etapa'].values:
        return False
        
    # 1. Atualiza a configuração do Kanban
    idx = kanban_config.index[kanban_config['Nome_Etapa'] == old_name].tolist()[0]
    kanban_config.at[idx, 'Nome_Etapa'] = new_name
    dfs['KanbanConfig'] = kanban_config
    
    # 2. Atualiza todos os leads que estavam na etapa antiga
    if not leads_df.empty:
        leads_df.loc[leads_df['Etapa_Atual'] == old_name, 'Etapa_Atual'] = new_name
        dfs['Leads'] = leads_df
        
    log_system_event(f"Coluna '{old_name}' renomeada para '{new_name}'.", "INFO")
    return True
# def update_kanban_stage_order ...