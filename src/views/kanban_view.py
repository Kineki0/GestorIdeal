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
        with st.form("form_create_lead_new_v3", clear_on_submit=True):
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
    p_filter = all_leads[all_leads['ID_Lead'].astype(int) == int(lead_id)]
    if p_filter.empty: return
    p = p_filter.iloc[0]
    
    with st.container(border=True):
        h1, h2 = st.columns([9, 1])
        h1.subheader(f"📄 #{p['ID_Lead']} - {p['Razao_Social']}")
        
        pdf_bytes = pdf_manager.generate_lead_pdf(p)
        st.download_button("📄 Baixar Ficha PDF", pdf_bytes, f"Lead_{p['ID_Lead']}.pdf", "application/pdf")

        if h2.button("✖️", key=f"close_{lead_id}"):
            st.session_state['show_fullscreen_details'] = False
            st.rerun()

        st.write("### ⚙️ Gestão de Fluxo")
        col_act1, col_act2, col_act3 = st.columns(3)
        stages = ETAPAS_KANBAN
        curr_idx = stages.index(p['Etapa_Atual'])
        
        if curr_idx > 0 and p['Etapa_Atual'] not in ['Ganhos', 'Perdidos']:
            if col_act1.button(f"⬅️ Voltar para {stages[curr_idx-1]}", use_container_width=True):
                repository.update_lead(lead_id, {'Etapa_Atual': stages[curr_idx-1]}, auth_manager.get_user(), f"Recuado para {stages[curr_idx-1]}")
                st.rerun()
        
        if curr_idx < len(stages) - 1 and p['Etapa_Atual'] not in ['Ganhos', 'Perdidos']:
            if col_act2.button(f"➡️ Avançar para {stages[curr_idx+1]}", use_container_width=True, type="primary"):
                repository.update_lead(lead_id, {'Etapa_Atual': stages[curr_idx+1]}, auth_manager.get_user(), f"Avançado para {stages[curr_idx+1]}")
                st.rerun()
        
        with col_act3:
            ga, pe = st.columns(2)
            if ga.button("🏆 Ganho", use_container_width=True):
                repository.update_lead(lead_id, {'Etapa_Atual': 'Ganhos'}, auth_manager.get_user(), "Venda!")
                st.rerun()
            if pe.button("📉 Perdido", use_container_width=True):
                repository.update_lead(lead_id, {'Etapa_Atual': 'Perdidos'}, auth_manager.get_user(), "Perdido")
                st.rerun()

        st.divider()
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Dados", "✅ Checklist", "📂 Anexos", "📜 Histórico"])
        
        with tab1:
            c1, c2 = st.columns(2)
            new_razao = c1.text_input("Razão Social", p['Razao_Social'])
            new_tel = c1.text_input("Telefone", p['Telefone'])
            new_nucleo = c1.selectbox("Núcleo", NUCLEOS, index=NUCLEOS.index(p['Nucleo']) if p['Nucleo'] in NUCLEOS else 0)
            new_prio = c2.selectbox("Prioridade", TAGS_PRIORIDADE, index=TAGS_PRIORIDADE.index(p['Prioridade']) if p['Prioridade'] in TAGS_PRIORIDADE else 1)
            new_prazo = c2.date_input("Próximo Retorno (Prazo)", value=pd.to_datetime(p['Prazo']).date() if pd.notna(p['Prazo']) else None)
            new_desc = st.text_area("Descrição do Processo (Editável)", p['Descricao'], height=150)
            
            if st.button("SALVAR ALTERAÇÕES", type="primary", use_container_width=True):
                repository.update_lead(lead_id, {'Razao_Social': new_razao, 'Telefone': new_tel, 'Nucleo': new_nucleo, 'Prioridade': new_prio, 'Prazo': new_prazo, 'Descricao': new_desc}, auth_manager.get_user())
                st.rerun()

        with tab2:
            st.write("### Checklist")
            items = json.loads(p['Checklist']) if p['Checklist'] and p['Checklist'] != "" else []
            new_item = st.text_input("Novo item de tarefa...")
            if st.button("Adicionar Item"):
                items.append({"task": new_item, "done": False})
                repository.update_lead(lead_id, {'Checklist': json.dumps(items)}, auth_manager.get_user())
                st.rerun()
            for i, item in enumerate(items):
                col_c, col_t = st.columns([0.1, 0.9])
                if col_c.checkbox("", value=item['done'], key=f"chk_{lead_id}_{i}") != item['done']:
                    items[i]['done'] = not item['done']
                    repository.update_lead(lead_id, {'Checklist': json.dumps(items)}, auth_manager.get_user())
                    st.rerun()
                col_t.write(item['task'])

        with tab3:
            if p['Etapa_Atual'] not in ['Ganhos', 'Perdidos']:
                up = st.file_uploader("Upload de Anexo", key=f"up_{lead_id}")
                if up:
                    anexos_manager.attach_file('Lead', lead_id, p['Razao_Social'], up, "Anexo", auth_manager.get_user())
                    st.rerun()
            else: st.info("Etapa final. Anexos não necessários.")

        with tab4:
            st.write("### Histórico e Comentários")
            with st.form(f"comment_{lead_id}"):
                msg = st.text_area("Nova nota...")
                if st.form_submit_button("POSTAR"):
                    repository.add_comment_to_lead_history(lead_id, auth_manager.get_user(), msg)
                    st.rerun()
            hist = repository.get_all('Historico')
            if not hist.empty:
                hist['ID_Lead_Clean'] = pd.to_numeric(hist['ID_Lead'], errors='coerce')
                hist = hist[hist['ID_Lead_Clean'] == int(lead_id)].sort_values('Timestamp', ascending=False)
            
            c_com, c_sys = st.columns(2)
            if not hist.empty:
                with c_com:
                    st.write("**Notas do Usuário**")
                    for _, r in hist[hist['Tipo'] == 'Comentário'].iterrows():
                        st.info(f"👤 {r['Usuario']} em {pd.to_datetime(r['Timestamp']).strftime('%d/%m %H:%M')}\n\n{r['Mensagem']}")
                with c_sys:
                    st.write("**Logs do Sistema**")
                    for _, r in hist[hist['Tipo'] == 'Ação'].iterrows():
                        st.caption(f"⚙️ {pd.to_datetime(r['Timestamp']).strftime('%d/%m %H:%M')} - Alterou {r['Campo']}")

def display():
    st.markdown("""
        <style>
            /* ESTILO CARD-BOTÃO COM QUEBRA DE LINHA */
            .stButton > button[key^="card_btn_"] {
                height: auto !important;
                padding: 15px !important;
                text-align: left !important;
                display: block !important;
                border-radius: 12px !important;
                border: 1px solid rgba(0,74,153,0.2) !important;
                background-color: var(--secondary-background-color) !important;
                transition: 0.3s !important;
                line-height: 1.5 !important;
            }
            .stButton > button[key^="card_btn_"] div p {
                white-space: pre-wrap !important; /* FORÇA A QUEBRA DE LINHA */
                word-wrap: break-word !important;
            }
            .stButton > button[key^="card_btn_"]:hover {
                border-color: #004a99 !important;
                box-shadow: 0 4px 12px rgba(0,74,153,0.1) !important;
                transform: translateY(-2px) !important;
            }
            
            [data-testid="column"] {
                border-right: 1px solid rgba(0,74,153,0.1) !important;
                padding: 10px 15px !important;
                min-width: 380px !important;
            }
            
            h3 { color: #004a99 !important; border-bottom: 2px solid #004a99; padding-bottom: 5px; margin-bottom: 20px !important; }
        </style>
    """, unsafe_allow_html=True)

    h1, h2 = st.columns([7, 3])
    h1.title("🎯 Fluxo de Operações")
    with h2:
        sort_order = st.selectbox("Ordenar por:", ["Mais Recentes", "Mais Antigos"])
        if st.button("＋ NOVO LEAD", use_container_width=True, type="primary"):
            st.session_state['show_create_lead_modal'] = True
            st.rerun()

    if st.session_state.get('show_create_lead_modal'): _display_create_lead_form()
    if st.session_state.get('show_fullscreen_details'): _display_lead_details_modal(st.session_state['selected_lead_id'])

    all_leads = repository.get_detailed_leads(sort_order)
    cols = st.columns(len(ETAPAS_KANBAN))
    
    for i, etapa in enumerate(ETAPAS_KANBAN):
        with cols[i]:
            st.markdown(f"### {etapa}")
            etapa_leads = all_leads[all_leads['Etapa_Atual'] == etapa]
            
            for _, p in etapa_leads.iterrows():
                dias = (datetime.now() - pd.to_datetime(p['Data_Entrada_Etapa'])).days if pd.notna(p.get('Data_Entrada_Etapa')) else 0
                criado = pd.to_datetime(p['Data_Criacao']).strftime('%d/%m/%y') if pd.notna(p['Data_Criacao']) else "N/A"
                retorno = pd.to_datetime(p['Prazo']).strftime('%d/%m/%y') if pd.notna(p['Prazo']) else "Sem data"
                
                # Texto formatado com quebras de linha reais (\n)
                label_text = (
                    f"🏢 {p['Razao_Social']}\n"
                    f"👤 {p['Nome_Contato']} ({dias}d na fase)\n"
                    f"📅 Criado: {criado} | ⏳ Retorno: {retorno}\n"
                    f"────────────────────\n"
                    f"💬 {p.get('Ultimo_Comentario', 'Sem notas')}"
                )
                
                # Container para o Card e o Botão de Nota Rápida
                with st.container():
                    # Card principal (Botão)
                    if st.button(label_text, key=f"card_btn_{p['ID_Lead']}", use_container_width=True):
                        st.session_state['selected_lead_id'] = p['ID_Lead']
                        st.session_state['show_fullscreen_details'] = True
                        st.rerun()
                    
                    # Botão de Nota Rápida (Abaixo do card)
                    with st.popover("💬 Nota Rápida", use_container_width=True):
                        quick_note = st.text_area("Escreva sua nota...", key=f"quick_note_area_{p['ID_Lead']}")
                        if st.button("Salvar Nota", key=f"btn_save_quick_{p['ID_Lead']}", type="primary"):
                            if quick_note:
                                repository.add_comment_to_lead_history(p['ID_Lead'], auth_manager.get_user(), quick_note)
                                st.success("Nota salva!")
                                st.rerun()
