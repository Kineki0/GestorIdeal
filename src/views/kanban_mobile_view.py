# kanban_mobile_view.py
import streamlit as st
import pandas as pd
from datetime import datetime
from data import repository_excel as repository
from services import auth_manager

def display():
    st.title("📱 Kanban Mobile")
    
    # 1. Carregar Dados
    stages = repository.get_kanban_stages()
    sort_order = st.selectbox("Ordenar por:", ["Mais Recentes", "Mais Antigos"], key="mob_sort")
    all_leads = repository.get_detailed_leads(sort_order)
    
    # 2. Seletor de Etapa (Estilo Abas/Dropdown para Mobile)
    selected_stage = st.selectbox("📍 Ver Etapa:", stages, key="mob_stage_selector")
    
    st.divider()
    
    # 3. Listagem de Cards para a Etapa Selecionada
    leads_in_stage = all_leads[all_leads['Etapa_Atual'] == selected_stage]
    
    if leads_in_stage.empty:
        st.info("Nenhum lead nesta etapa.")
    else:
        for _, p in leads_in_stage.iterrows():
            with st.container(border=True):
                # Cabeçalho do Card
                st.subheader(f"🏢 {p['Razao_Social']}")
                st.write(f"👤 {p['Nome_Contato']} | 📞 {p['Telefone']}")
                
                # SLA / Datas
                d_entrada = pd.to_datetime(p['Data_Entrada_Etapa']) if pd.notna(p['Data_Entrada_Etapa']) else pd.to_datetime(p['Data_Criacao'])
                dias = (datetime.now() - d_entrada).days
                aging = "⚠️ **ESTAGNADO**" if dias >= 5 and selected_stage not in ['Ganhos', 'Perdidos'] else ""
                if aging: st.warning(aging)
                
                st.caption(f"🕒 {dias} dias na fase | ⏳ Retorno: {pd.to_datetime(p['Prazo']).strftime('%d/%m/%y') if pd.notna(p['Prazo']) else 'N/A'}")
                
                # Comentário
                st.info(f"💬 {p.get('Ultimo_Comentario', 'Sem notas')}")
                
                # Ações Mobile
                c1, c2 = st.columns(2)
                if c1.button("📄 Detalhes", key=f"mob_det_{p['ID_Lead']}", use_container_width=True):
                    st.session_state['selected_lead_id'] = p['ID_Lead']
                    st.session_state['show_fullscreen_details'] = True
                    st.rerun()
                
                with c2.popover("➕ Nota", use_container_width=True):
                    msg = st.text_area("Nota rápida:", key=f"mob_note_{p['ID_Lead']}")
                    if st.button("Salvar", key=f"mob_save_{p['ID_Lead']}", type="primary", use_container_width=True):
                        repository.add_comment_to_lead_history(p['ID_Lead'], auth_manager.get_user(), msg)
                        st.rerun()

    # Reaproveita o modal de detalhes original (ele já é responsivo no CSS que fizemos)
    from views import kanban_view
    if st.session_state.get('show_fullscreen_details'):
        kanban_view._display_lead_details_modal(st.session_state['selected_lead_id'])
