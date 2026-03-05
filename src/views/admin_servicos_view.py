# admin_servicos_view.py
import streamlit as st
from data import repository_excel as repository

def display():
    """Exibe a página de gerenciamento de serviços com opções de CRUD."""
    st.header("Gerenciamento de Serviços")

    # --- Formulário para adicionar novo serviço ---
    with st.expander("➕ Adicionar Novo Serviço", expanded=False):
        with st.form("new_service_form", clear_on_submit=True):
            nome_servico = st.text_input("Nome do Serviço")
            submitted = st.form_submit_button("Adicionar Serviço")
            if submitted and nome_servico:
                new_id = repository.create_service(nome_servico)
                if new_id:
                    st.success(f"Serviço '{nome_servico}' adicionado com sucesso!")
                    st.rerun()
                else:
                    st.warning(f"Serviço '{nome_servico}' já existe.")
            elif submitted:
                st.error("O nome do serviço não pode ser vazio.")
    
    st.divider()

    # --- Seção para editar ou inativar serviço ---
    st.subheader("Editar ou Inativar Serviços")
    servicos_df = repository.get_all('Servicos')
    
    if servicos_df.empty:
        st.info("Nenhum serviço cadastrado para editar.")
    else:
        servico_list = servicos_df.sort_values(by='Nome_Servico')
        servico_map = {row['Nome_Servico']: row['ID_Servico'] for _, row in servico_list.iterrows()}
        
        selected_servico_nome = st.selectbox(
            "Selecione um serviço para modificar",
            options=servico_map.keys(),
            index=None,
            placeholder="Escolha um serviço..."
        )

        if selected_servico_nome:
            selected_id = servico_map[selected_servico_nome]
            servico_atual = servico_list[servico_list['ID_Servico'] == selected_id].iloc[0]
            
            st.divider()

            # --- Formulário de Edição de Nome ---
            with st.form(f"edit_service_name_{selected_id}"):
                st.markdown(f"##### Editar Nome de '{servico_atual['Nome_Servico']}'")
                novo_nome = st.text_input("Novo nome do serviço", value=servico_atual['Nome_Servico'])
                edit_submitted = st.form_submit_button("Salvar Novo Nome")
                
                if edit_submitted and novo_nome != servico_atual['Nome_Servico']:
                    repository.update_entity('Servicos', 'ID_Servico', selected_id, {'Nome_Servico': novo_nome})
                    st.success(f"Nome do serviço alterado para '{novo_nome}'!")
                    st.rerun()

            st.divider()

            # --- Seção de Ativação/Inativação ---
            st.markdown("##### Status do Serviço")
            status_atual = servico_atual['Ativo']
            
            if status_atual:
                st.success("Este serviço está **Ativo**.")
                if st.button("Inativar Serviço", key=f"deactivate_servico_{selected_id}", type="primary"):
                    repository.update_entity('Servicos', 'ID_Servico', selected_id, {'Ativo': False})
                    st.warning(f"Serviço '{servico_atual['Nome_Servico']}' foi inativado.")
                    st.rerun()
            else:
                st.error("Este serviço está **Inativo**.")
                if st.button("Reativar Serviço", key=f"activate_servico_{selected_id}"):
                    repository.update_entity('Servicos', 'ID_Servico', selected_id, {'Ativo': True})
                    st.success(f"Serviço '{servico_atual['Nome_Servico']}' foi reativado.")
                    st.rerun()


    st.divider()
    # --- Lista de todos os serviços ---
    st.subheader("Visão Geral dos Serviços")
    st.dataframe(servicos_df, width='stretch')