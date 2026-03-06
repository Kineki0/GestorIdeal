# admin_jarvis_brain_view.py
import streamlit as st
import pandas as pd
from data import repository_excel as repository
from datetime import datetime

def display():
    st.title("🧠 Centro de Treinamento do Jarvis")
    st.write("Gerencie o conhecimento do assistente e aprove sugestões dos usuários.")

    # 1. FORMULÁRIO PARA NOVO CONHECIMENTO (CURADORIA)
    with st.expander("🆕 Adicionar Novo Conhecimento Manualmente"):
        with st.form("form_new_knowledge"):
            palavra = st.text_input("Palavra-Chave (O que o usuário deve digitar)")
            resposta = st.text_area("Resposta do Jarvis")
            if st.form_submit_button("ENSINAR AO JARVIS"):
                if palavra and resposta:
                    # Adiciona já aprovado
                    dfs = repository.get_session_dfs()
                    df = dfs['Jarvis_Brain']
                    new_id = (df['ID_Conhecimento'].max() + 1) if not df.empty else 1
                    new_row = {
                        'ID_Conhecimento': new_id, 'Palavra_Chave': palavra.lower().strip(), 
                        'Resposta': resposta, 'Status': 'Aprovado', 
                        'Usuario_Sugeriu': 'Admin', 'Data_Criacao': datetime.now()
                    }
                    dfs['Jarvis_Brain'] = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    repository.commit_to_file()
                    st.success("Jarvis aprendeu com sucesso!")
                    st.rerun()

    st.divider()

    # 2. TABELA DE GESTÃO (EDIÇÃO E APROVAÇÃO)
    st.subheader("📚 Base de Conhecimento Atual")
    kb_df = repository.get_all('Jarvis_Brain')
    
    if kb_df.empty:
        st.info("O cérebro do Jarvis está vazio. Adicione conhecimentos acima.")
    else:
        # Editor de dados para o Admin
        edited_kb = st.data_editor(
            kb_df,
            num_rows="dynamic",
            key="brain_editor",
            column_config={
                "ID_Conhecimento": st.column_config.NumberColumn("ID", disabled=True),
                "Palavra_Chave": st.column_config.TextColumn("Palavra-Chave", required=True),
                "Resposta": st.column_config.TextColumn("Resposta", required=True),
                "Status": st.column_config.SelectboxColumn("Status", options=["Aprovado", "Pendente", "Rejeitado"]),
                "Usuario_Sugeriu": st.column_config.TextColumn("Sugerido por", disabled=True),
                "Data_Criacao": st.column_config.DatetimeColumn("Data", disabled=True)
            },
            hide_index=True,
            use_container_width=True
        )

        if st.button("SALVAR ALTERAÇÕES NO CÉREBRO", type="primary"):
            repository.sync_knowledge_base(edited_kb)
            st.success("Base de conhecimento sincronizada!")
            st.rerun()
