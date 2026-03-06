# kanban_mobile_view.py
import streamlit as st
import pandas as pd
from datetime import datetime
from data import repository_excel as repository
from services import auth_manager
from views import kanban_view

def display():
    st.title("📱 Kanban Mobile")
    
    # 1. Botão de Novo Lead (Topo)
    if st.button("＋ NOVO LEAD", use_container_width=True, type="primary"):
        st.session_state['show_create_lead_modal'] = True
        st.rerun()

    # Exibe o formulário de cadastro se o modal estiver ativo
    if st.session_state.get('show_create_lead_modal'):
        kanban_view._display_create_lead_form()

    st.divider()

    # 2. Carregar Dados e Filtros Rápidos
    stages = repository.get_kanban_stages()
    c1, c2 = st.columns([1.5, 1])
    with c1:
        selected_stage = st.selectbox("📍 Etapa:", stages, key="mob_stage_selector")
    with c2:
        sort_order = st.selectbox("Order:", ["Recentes", "Antigos"], key="mob_sort", label_visibility="collapsed")
    
    all_leads = repository.get_detailed_leads("Mais Recentes" if sort_order == "Recentes" else "Mais Antigos")
    
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
                act1, act2 = st.columns(2)
                if act1.button("📄 Detalhes", key=f"mob_det_{p['ID_Lead']}", use_container_width=True):
                    st.session_state['selected_lead_id'] = p['ID_Lead']
                    st.session_state['show_fullscreen_details'] = True
                    st.rerun()
                
                with act2.popover("➕ Nota", use_container_width=True):
                    msg = st.text_area("Nota rápida:", key=f"mob_note_{p['ID_Lead']}")
                    if st.button("Salvar", key=f"mob_save_{p['ID_Lead']}", type="primary", use_container_width=True):
                        repository.add_comment_to_lead_history(p['ID_Lead'], auth_manager.get_user(), msg)
                        st.rerun()

    # Reaproveita o modal de detalhes original
    if st.session_state.get('show_fullscreen_details'):
        kanban_view._display_lead_details_modal(st.session_state['selected_lead_id'])
