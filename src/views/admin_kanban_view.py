# admin_kanban_view.py
import streamlit as st
from data import repository_excel as repository

def display():
    st.title("Administração do Kanban")

    st.subheader("Gerenciar Etapas do Kanban")

    # Carregar etapas atuais
    kanban_stages_df = repository.get_all('KanbanConfig').sort_values(by='Ordem').reset_index(drop=True)

    st.info("Use o editor abaixo para reordenar, renomear ou remover etapas. Para adicionar uma nova etapa, use o formulário mais abaixo.")

    # Usar o st.data_editor para permitir a edição
    edited_df = st.data_editor(
        kanban_stages_df,
        num_rows="dynamic",
        key="kanban_editor",
        column_config={
            "ID_Etapa": st.column_config.NumberColumn("ID", disabled=True),
            "Nome_Etapa": st.column_config.TextColumn("Nome da Etapa", required=True),
            "Ordem": st.column_config.NumberColumn("Ordem", disabled=True)
        },
        hide_index=True,
    )

    if st.button("Salvar Alterações", key="save_kanban_changes"):
        repository.sync_kanban_stages(edited_df)
        st.success("Alterações salvas com sucesso!")
        st.rerun()

