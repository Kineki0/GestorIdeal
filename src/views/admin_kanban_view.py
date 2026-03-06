import streamlit as st
import pandas as pd
import time
from data import repository_excel as repository

def display():
    st.title("⚙️ Configuração do Fluxo (Kanban)")
    
    # --- BOTÃO DE EMERGÊNCIA (PARA REMOVER NAN) ---
    with st.expander("🛠️ Ferramentas de Manutenção", expanded=False):
        st.warning("Use estas ferramentas se houver erros visuais ou registros 'nan'.")
        if st.button("🔥 LIMPEZA PROFUNDA (RESTAURAR PADRÕES)", use_container_width=True):
            from config import ETAPAS_KANBAN
            new_df = pd.DataFrame({
                'ID_Etapa': range(1, len(ETAPAS_KANBAN) + 1),
                'Nome_Etapa': ETAPAS_KANBAN,
                'Ordem': range(len(ETAPAS_KANBAN))
            })
            repository.sync_kanban_stages(new_df)
            # Força a limpeza do cache de sessão
            if 'db_dfs' in st.session_state:
                del st.session_state.db_dfs
            st.success("✅ Sistema restaurado! Reiniciando...")
            time.sleep(1)
            st.rerun()

    st.markdown("""
        Gerencie as etapas do seu processo comercial. Você pode reordenar, 
        renomear ou adicionar novas fases para personalizar o funil de vendas.
    """)

    # 1. Carregar Configurações Atuais
    dfs = repository.get_session_dfs()
    kanban_df = dfs.get('KanbanConfig', pd.DataFrame())
    
    if kanban_df.empty:
        st.warning("⚠️ Nenhuma configuração de Kanban encontrada. Inicializando padrão...")
        from config import ETAPAS_KANBAN
        kanban_df = pd.DataFrame({
            'ID_Etapa': range(1, len(ETAPAS_KANBAN) + 1),
            'Nome_Etapa': ETAPAS_KANBAN,
            'Ordem': range(len(ETAPAS_KANBAN))
        })
        repository.sync_kanban_stages(kanban_df)
    
    kanban_df = kanban_df.sort_values('Ordem').reset_index(drop=True)

    # 2. Exibição e Reordenação
    st.subheader("🔄 Ordem das Etapas")
    
    for i, row in kanban_df.iterrows():
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([0.1, 5, 1, 1])
            
            c1.write(f"**{i+1}**")
            c2.write(f"📂 **{row['Nome_Etapa']}**")
            
            # Botões de Reordenação
            if c3.button("🔼", key=f"up_{row['ID_Etapa']}", disabled=(i == 0), use_container_width=True):
                # Troca de ordem com o anterior
                kanban_df.at[i, 'Ordem'], kanban_df.at[i-1, 'Ordem'] = kanban_df.at[i-1, 'Ordem'], kanban_df.at[i, 'Ordem']
                repository.sync_kanban_stages(kanban_df)
                st.rerun()
                
            if c4.button("🔽", key=f"down_{row['ID_Etapa']}", disabled=(i == len(kanban_df)-1), use_container_width=True):
                # Troca de ordem com o próximo
                kanban_df.at[i, 'Ordem'], kanban_df.at[i+1, 'Ordem'] = kanban_df.at[i+1, 'Ordem'], kanban_df.at[i, 'Ordem']
                repository.sync_kanban_stages(kanban_df)
                st.rerun()

    st.divider()

    # 3. Adicionar Nova Etapa
    st.subheader("➕ Adicionar Nova Etapa")
    with st.form("new_stage_form", clear_on_submit=True):
        new_name = st.text_input("Nome da Nova Etapa", placeholder="Ex: Pós-Venda, Auditoria...")
        if st.form_submit_button("CRIAR ETAPA", use_container_width=True, type="primary"):
            if new_name:
                if new_name in kanban_df['Nome_Etapa'].values:
                    st.error("❌ Já existe uma etapa com este nome.")
                else:
                    new_id = (kanban_df['ID_Etapa'].max() + 1) if not kanban_df.empty else 1
                    new_order = (kanban_df['Ordem'].max() + 1) if not kanban_df.empty else 0
                    new_row = pd.DataFrame([{'ID_Etapa': new_id, 'Nome_Etapa': new_name, 'Ordem': new_order}])
                    repository.sync_kanban_stages(pd.concat([kanban_df, new_row], ignore_index=True))
                    st.success(f"✅ Etapa '{new_name}' adicionada!")
                    st.rerun()
            else:
                st.warning("⚠️ Digite um nome para a etapa.")

    st.divider()

    # 4. Renomear ou Remover
    st.subheader("📝 Editar ou Remover Etapas")
    leads_df = dfs.get('Leads', pd.DataFrame())
    
    selected_stage = st.selectbox("Selecione uma etapa para editar", kanban_df['Nome_Etapa'].tolist())
    
    if selected_stage and not kanban_df[kanban_df['Nome_Etapa'] == selected_stage].empty:
        stage_data = kanban_df[kanban_df['Nome_Etapa'] == selected_stage].iloc[0]
        
        c1, c2 = st.columns(2)
        with c1:
            new_name_edit = st.text_input("Novo Nome", value=selected_stage)
            if st.button("SALVAR RENOMEAÇÃO", use_container_width=True):
                if new_name_edit and new_name_edit != selected_stage:
                    # Atualiza na configuração
                    kanban_df.loc[kanban_df['Nome_Etapa'] == selected_stage, 'Nome_Etapa'] = new_name_edit
                    repository.sync_kanban_stages(kanban_df)
                    
                    # Atualiza os leads que estavam nessa etapa
                    if not leads_df.empty and 'Etapa_Atual' in leads_df.columns:
                        leads_df.loc[leads_df['Etapa_Atual'] == selected_stage, 'Etapa_Atual'] = new_name_edit
                        # Aqui precisaríamos de um commit global ou atualizar no session_state
                        st.success(f"✅ Etapa renomeada para '{new_name_edit}'!")
                        st.rerun()
        
        with c2:
            st.warning("Ações Críticas")
            leads_count = 0
            if not leads_df.empty and 'Etapa_Atual' in leads_df.columns:
                leads_count = len(leads_df[leads_df['Etapa_Atual'] == selected_stage])
            
            if leads_count > 0:
                st.error(f"⚠️ Existem {leads_count} leads nesta etapa.")
                if st.button(f"🗑️ EXCLUIR TODOS OS {leads_count} LEADS", use_container_width=True, type="primary"):
                    if repository.delete_leads_by_stage(selected_stage):
                        st.success(f"✅ Todos os leads de '{selected_stage}' foram removidos.")
                        st.rerun()
                
                st.caption("Remova os leads acima antes de poder excluir a etapa.")
                st.button("🗑️ EXCLUIR ETAPA", disabled=True, use_container_width=True)
            else:
                if st.button("🗑️ EXCLUIR ETAPA", type="secondary", use_container_width=True):
                    new_df = kanban_df[kanban_df['Nome_Etapa'] != selected_stage]
                    repository.sync_kanban_stages(new_df)
                    st.success("✅ Etapa removida com sucesso!")
                    st.rerun()
