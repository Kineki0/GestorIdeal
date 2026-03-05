# anexos_manager.py
import streamlit as st
from services import drive_manager
from data import repository_excel as repository
from datetime import datetime
import os

def attach_file(tipo_referencia, id_referencia, nome_referencia, uploaded_file, descricao, user):
    """
    Orquestra o processo completo de anexo de um arquivo.
    1. Define a estrutura de pastas.
    2. Cria as pastas no Google Drive, se necessário.
    3. Faz o upload do arquivo.
    4. Registra o anexo no banco de dados Excel.
    """
    root_folder_id = st.secrets.get("DRIVE_ROOT_FOLDER_ID")
    if not root_folder_id or root_folder_id == "SEU_ID_DA_PASTA_RAIZ_AQUI":
        st.error("O ID da pasta raiz do Google Drive não está configurado em .streamlit/secrets.toml.")
        return False

    # 1. Define a estrutura e cria as pastas
    try:
        # Pasta de Data (ex: 2026 / Março)
        date_folder_id = drive_manager.get_date_folder_structure(root_folder_id)
        
        # Pasta de nível de Categoria (Clientes, Leads, etc.) dentro da data
        main_type_folder_id = drive_manager.find_or_create_folder(f"{tipo_referencia}s", date_folder_id)
        if not main_type_folder_id: return False

        # Pasta de segundo nível (ID da Referência)
        destination_folder_id = drive_manager.find_or_create_folder(str(id_referencia), main_type_folder_id)
        if not destination_folder_id: return False

    except Exception as e:
        st.error(f"Falha ao preparar a estrutura de pastas no Drive: {e}")
        return False

    # 2. Padroniza o nome do arquivo e faz o upload
    timestamp = datetime.now().strftime("%Y%m%d")
    original_name, original_ext = os.path.splitext(uploaded_file.name)
    safe_descricao = "".join(x for x in descricao if x.isalnum() or x in " _-").strip()
    
    final_file_name = f"{timestamp} - {safe_descricao or original_name}{original_ext}"

    upload_result = drive_manager.upload_file(uploaded_file, final_file_name, destination_folder_id)

    if not upload_result:
        st.error("O upload para o Google Drive falhou.")
        return False

    # 3. Registra o anexo no Excel
    try:
        repository.create_anexo_record(
            tipo_referencia=tipo_referencia,
            id_referencia=id_referencia,
            nome_arquivo=final_file_name,
            tipo_arquivo=uploaded_file.type,
            link_drive=upload_result['link'],
            usuario_envio=user['Nome'],
            observacao=descricao
        )
        st.success(f"Arquivo '{final_file_name}' anexado com sucesso!")
        return True
    except Exception as e:
        st.error(f"Upload para o Drive bem-sucedido, mas falha ao registrar no Excel: {e}")
        # Idealmente, aqui teríamos uma lógica para tentar reverter o upload ou notificar um admin.
        return False
