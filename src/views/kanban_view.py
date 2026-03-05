# kanban_view.py
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from data import repository_excel as repository
from services import auth_manager, anexos_manager, pdf_manager
from config import ETAPAS_KANBAN, NUCLEOS, TAGS_PRIORIDADE, TAGS_RISCO, TAGS_ESFORCO, TAGS_STATUS

def _display_create_lead_form():
    if not st.session_state.get('show_create_lead_modal', False): return
    with st.container(border=True):
        st.subheader("🚀 Novo Lead")
        with st.form("form_create_lead_new", clear_on_submit=True):
            c1, c2 = st.columns(2)
            razao = c1.text_input("Razão Social *")
            telefone = c1.text_input("Telefone *")
            contato = c2.text_input("Contato *")
            cnpj = c2.text_input("CNPJ *")
            email = st.text_input("Email (Opcional)")
            
            if st.form_submit_button("CADASTRAR LEAD", use_container_width=True, type="primary"):
                if not razao or not telefone or not contato or not cnpj:
                    st.error("Preencha todos os campos obrigatórios (*)")
                else:
                    repository.create_lead({'Razao_Social': razao, 'Telefone': telefone, 'Nome_Contato': contato, 'CNPJ': cnpj, 'Email': email}, auth_manager.get_user())
                    st.session_state['show_create_lead_modal'] = False
                    st.rerun()
        if st.button("CANCELAR", use_container_width=True):
            st.session_state['show_create_lead_modal'] = False
            st.rerun()

def _display_lead_details_modal(lead_id):
    if not st.session_state.get('show_fullscreen_details', False): return
    all_leads = repository.get_detailed_leads()
    p = all_leads[all_leads['ID_Lead'].astype(int) == int(lead_id)].iloc[0]
    
    with st.container(border=True):
        h1, h2 = st.columns([9, 1])
        h1.subheader(f"📄 #{p['ID_Lead']} - {p['Razao_Social']}")
        if h2.button("✖️", key=f"close_{lead_id}"):
            st.session_state['show_fullscreen_details'] = False
            st.rerun()

        # --- AÇÕES E FLUXO ---
        st.write("### ⚙️ Gestão")
        col_act1, col_act2, col_act3 = st.columns(3)
        
        stages = ETAPAS_KANBAN
        curr_idx = stages.index(p['Etapa_Atual'])
        
        # Botão Voltar (Se não for a primeira e nem Ganhos/Perdidos)
        if curr_idx > 0 and p['Etapa_Atual'] not in ['Ganhos', 'Perdidos']:
            if col_act1.button(f"⬅️ Voltar para {stages[curr_idx-1]}", use_container_width=True):
                repository.update_lead(lead_id, {'Etapa_Atual': stages[curr_idx-1]}, auth_manager.get_user(), f"Recuado para {stages[curr_idx-1]}")
                st.rerun()
        
        # Botão Avançar
        if curr_idx < len(stages) - 1 and p['Etapa_Atual'] not in ['Ganhos', 'Perdidos']:
            if col_act2.button(f"➡️ Avançar para {stages[curr_idx+1]}", use_container_width=True, type="primary"):
                repository.update_lead(lead_id, {'Etapa_Atual': stages[curr_idx+1]}, auth_manager.get_user(), f"Avançado para {stages[curr_idx+1]}")
                st.rerun()
        
        # Botão Ganhos/Perdidos (Atalhos)
        with col_act3:
            ga, pe = st.columns(2)
            if ga.button("🏆 Ganho", use_container_width=True):
                repository.update_lead(lead_id, {'Etapa_Atual': 'Ganhos'}, auth_manager.get_user(), "Venda Concluída!")
                st.rerun()
            if pe.button("📉 Perdido", use_container_width=True):
                repository.update_lead(lead_id, {'Etapa_Atual': 'Perdidos'}, auth_manager.get_user(), "Lead Perdido")
                st.rerun()

        st.divider()

        # --- INFORMAÇÕES E EDIÇÃO ---
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Dados", "✅ Checklist", "📂 Anexos", "📜 Histórico"])
        
        with tab1:
            c1, c2 = st.columns(2)
            with c1:
                new_razao = st.text_input("Razão Social", p['Razao_Social'])
                new_tel = st.text_input("Telefone", p['Telefone'])
                new_nucleo = st.selectbox("Núcleo", NUCLEOS, index=NUCLEOS.index(p['Nucleo']) if p['Nucleo'] in NUCLEOS else 0)
            with c2:
                new_prio = st.selectbox("Prioridade", TAGS_PRIORIDADE, index=TAGS_PRIORIDADE.index(p['Prioridade']) if p['Prioridade'] in TAGS_PRIORIDADE else 1)
                new_prazo = st.date_input("Próximo Retorno (Prazo)", value=pd.to_datetime(p['Prazo']).date() if pd.notna(p['Prazo']) else None)
            
            new_desc = st.text_area("Descrição do Processo", p['Descricao'], height=150)
            
            if st.button("SALVAR ALTERAÇÕES", type="primary", use_container_width=True):
                repository.update_lead(lead_id, {
                    'Razao_Social': new_razao, 'Telefone': new_tel, 'Nucleo': new_nucleo,
                    'Prioridade': new_prio, 'Prazo': new_prazo, 'Descricao': new_desc
                }, auth_manager.get_user())
                st.rerun()

        with tab2:
            st.write("### Checklist de Atividades")
            items = json.loads(p['Checklist']) if p['Checklist'] and p['Checklist'] != "" else []
            new_item = st.text_input("Novo item...")
            if st.button("Adicionar"):
                items.append({"task": new_item, "done": False})
                repository.update_lead(lead_id, {'Checklist': json.dumps(items)}, auth_manager.get_user())
                st.rerun()
            
            for i, item in enumerate(items):
                col_check, col_text = st.columns([0.1, 0.9])
                checked = col_check.checkbox("", value=item['done'], key=f"check_{lead_id}_{i}")
                if checked != item['done']:
                    items[i]['done'] = checked
                    repository.update_lead(lead_id, {'Checklist': json.dumps(items)}, auth_manager.get_user())
                    st.rerun()
                col_text.write(item['task'])

        with tab3:
            if p['Etapa_Atual'] not in ['Ganhos', 'Perdidos']:
                st.write("### 📂 Upload de Arquivos")
                up = st.file_uploader("Novo arquivo", key=f"up_{lead_id}")
                if up:
                    anexos_manager.attach_file('Lead', lead_id, p['Razao_Social'], up, "Anexo de Fluxo", auth_manager.get_user())
                    st.rerun()
            else:
                st.info("Anexos não são obrigatórios nesta etapa final.")

        with tab4:
            st.write("### 💬 Comentários")
            with st.form(f"comment_{lead_id}"):
                msg = st.text_area("Nova nota...")
                if st.form_submit_button("POSTAR"):
                    repository.add_comment_to_lead_history(lead_id, auth_manager.get_user(), msg)
                    st.rerun()
            
            hist = repository.get_all('Historico')
            if not hist.empty:
                # Filtragem segura convertendo para numérico e tratando erros (NaNs)
                hist['ID_Lead_Num'] = pd.to_numeric(hist['ID_Lead'], errors='coerce')
                hist = hist[hist['ID_Lead_Num'] == int(lead_id)].sort_values('Timestamp', ascending=False)
            
            c_com, c_sys = st.columns(2)
            if not hist.empty:
                with c_com:
                    st.write("**Notas do Usuário**")
                    comentarios = hist[hist['Tipo'] == 'Comentário']
                    for _, r in comentarios.iterrows():
                        st.caption(f"📅 {pd.to_datetime(r['Timestamp']).strftime('%d/%m %H:%M')} - {r['Usuario']}")
                        st.info(r['Mensagem'])
                with c_sys:
                    st.write("**Logs do Sistema**")
                    acoes = hist[hist['Tipo'] == 'Ação']
                    for _, r in acoes.iterrows():
                        st.caption(f"⚙️ {pd.to_datetime(r['Timestamp']).strftime('%d/%m %H:%M')}")
                        st.write(f"Modificou **{r['Campo']}**")
            else:
                st.info("Nenhum histórico encontrado para este lead.")

def display():
    st.markdown("""
        <style>
            [data-testid="column"] { 
                min-width: 350px !important; 
                border-right: 1px solid rgba(0,74,153,0.1);
                padding: 10px !important;
            }
            .kanban-card {
                background-color: var(--secondary-background-color);
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 10px;
                border: 1px solid rgba(0,74,153,0.2);
                cursor: pointer;
                transition: 0.3s;
            }
            .kanban-card:hover { border-color: #004a99; transform: translateY(-2px); }
            .sla-tag { font-size: 0.7rem; background: #004a99; color: white; padding: 2px 6px; border-radius: 5px; float: right; }
        </style>
    """, unsafe_allow_html=True)

    # Header e Filtros
    h1, h2 = st.columns([7, 3])
    h1.title("🎯 Fluxo de Operações")
    with h2:
        sort_order = st.selectbox("Ordenar por:", ["Mais Recentes", "Mais Antigos"])
        if st.button("＋ NOVO LEAD", use_container_width=True, type="primary"):
            st.session_state['show_create_lead_modal'] = True
            st.rerun()

    if st.session_state.get('show_create_lead_modal'): _display_create_lead_form()
    if st.session_state.get('show_fullscreen_details'): _display_lead_details_modal(st.session_state['selected_lead_id'])

    # Grid
    all_leads = repository.get_detailed_leads(sort_order)
    cols = st.columns(len(ETAPAS_KANBAN))
    
    for i, etapa in enumerate(ETAPAS_KANBAN):
        with cols[i]:
            st.markdown(f"### {etapa}")
            etapa_leads = all_leads[all_leads['Etapa_Atual'] == etapa]
            
            for _, p in etapa_leads.iterrows():
                # Cálculo de dias na etapa
                dias = (datetime.now() - pd.to_datetime(p['Data_Entrada_Etapa'])).days if pd.notna(p.get('Data_Entrada_Etapa')) else 0
                
                # Card como botão invisível sobreposto
                if st.button(
                    label=f"OPEN_CARD_{p['ID_Lead']}", 
                    key=f"card_btn_{p['ID_Lead']}", 
                    use_container_width=True,
                    help=f"Clique para abrir #{p['ID_Lead']}"
                ):
                    st.session_state['selected_lead_id'] = p['ID_Lead']
                    st.session_state['show_fullscreen_details'] = True
                    st.rerun()

                # Visual do Card (posicionado logo abaixo do botão invisível via CSS para dar efeito de clique)
                st.markdown(f"""
                    <div class="kanban-card" style="margin-top: -45px; pointer-events: none;">
                        <span class="sla-tag">{dias}d</span>
                        <div style="font-weight:bold; color:#004a99;">{p['Razao_Social']}</div>
                        <div style="font-size:0.8rem; opacity:0.7;">👤 {p['Nome_Contato']}</div>
                        <div style="font-size:0.8rem; margin-top:5px; font-style:italic;">💬 {p.get('Ultimo_Comentario', 'Sem notas')}</div>
                    </div>
                """, unsafe_allow_html=True)
