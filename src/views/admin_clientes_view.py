# admin_clientes_view.py
import streamlit as st
from data import repository_excel as repository

def display():
    """Exibe a página de gerenciamento de clientes com opções de CRUD."""
    st.header("Gerenciamento de Clientes")

    # --- Formulário para adicionar novo cliente ---
    with st.expander("➕ Adicionar Novo Cliente", expanded=False):
        with st.form("new_client_form", clear_on_submit=True):
            nome_cliente = st.text_input("Nome do Cliente")
            submitted = st.form_submit_button("Adicionar Cliente")
            if submitted and nome_cliente:
                new_id = repository.create_client(nome_cliente)
                if new_id:
                    st.success(f"Cliente '{nome_cliente}' adicionado com sucesso!")
                    st.rerun()
                else:
                    st.warning(f"Cliente '{nome_cliente}' já existe.")
            elif submitted:
                st.error("O nome do cliente não pode ser vazio.")
    
    st.divider()

    # --- Seção para editar ou inativar cliente ---
    st.subheader("Editar ou Inativar Clientes")
    clientes_df = repository.get_all('Clientes')
    
    if clientes_df.empty:
        st.info("Nenhum cliente cadastrado para editar.")
    else:
        # Cria um mapeamento de nome para ID para o selectbox
        cliente_list = clientes_df.sort_values(by='Nome_Cliente')
        cliente_map = {row['Nome_Cliente']: row['ID_Cliente'] for _, row in cliente_list.iterrows()}
        
        selected_cliente_nome = st.selectbox(
            "Selecione um cliente para modificar",
            options=cliente_map.keys(),
            index=None,
            placeholder="Escolha um cliente..."
        )

        if selected_cliente_nome:
            selected_id = cliente_map[selected_cliente_nome]
            cliente_atual = cliente_list[cliente_list['ID_Cliente'] == selected_id].iloc[0]
            
            st.divider()
            
            # --- Formulário de Edição de Nome ---
            with st.form(f"edit_client_name_{selected_id}"):
                st.markdown(f"##### Editar Nome de '{cliente_atual['Nome_Cliente']}'")
                novo_nome = st.text_input("Novo nome do cliente", value=cliente_atual['Nome_Cliente'])
                edit_submitted = st.form_submit_button("Salvar Novo Nome")
                
                if edit_submitted and novo_nome != cliente_atual['Nome_Cliente']:
                    repository.update_entity('Clientes', 'ID_Cliente', selected_id, {'Nome_Cliente': novo_nome})
                    st.success(f"Nome do cliente alterado para '{novo_nome}'!")
                    st.rerun()

            st.divider()

            # --- Seção de Ativação/Inativação ---
            st.markdown("##### Status do Cliente")
            status_atual = cliente_atual['Ativo']
            
            if status_atual:
                st.success("Este cliente está **Ativo**.")
                if st.button("Inativar Cliente", key=f"deactivate_cliente_{selected_id}", type="primary"):
                    repository.update_entity('Clientes', 'ID_Cliente', selected_id, {'Ativo': False})
                    st.warning(f"Cliente '{cliente_atual['Nome_Cliente']}' foi inativado.")
                    st.rerun()
            else:
                st.error("Este cliente está **Inativo**.")
                if st.button("Reativar Cliente", key=f"activate_cliente_{selected_id}"):
                    repository.update_entity('Clientes', 'ID_Cliente', selected_id, {'Ativo': True})
                    st.success(f"Cliente '{cliente_atual['Nome_Cliente']}' foi reativado.")
                    st.rerun()


    st.divider()
    # --- Lista de todos os clientes ---
    st.subheader("Visão Geral dos Clientes")
    st.dataframe(clientes_df, width='stretch')