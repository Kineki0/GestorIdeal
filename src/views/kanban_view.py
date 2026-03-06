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
        st.subheader("🚀 Cadastro de Novo Lead")
        with st.form("form_create_lead_strict", clear_on_submit=True):
            c1, c2 = st.columns(2)
            razao = c1.text_input("Razão Social *")
            telefone = c1.text_input("Telefone (WhatsApp) *")
            contato = c2.text_input("Nome do Contato *")
            cnpj = c2.text_input("CNPJ *")
            email = st.text_input("Email (Opcional)")
            
            st.info("💡 Prazo e Observações serão definidos na etapa 'Em Progresso'.")
            
            if st.form_submit_button("CADASTRAR NO SISTEMA", use_container_width=True, type="primary"):
                # VALIDAÇÃO RIGOROSA conforme solicitado
                if not razao or not telefone or not contato or not cnpj:
                    st.error("❌ ERRO: Razão Social, Telefone, Contato e CNPJ são OBRIGATÓRIOS.")
                else:
                    repository.create_lead({
                        'Razao_Social': razao, 
                        'Telefone': telefone, 
                        'Nome_Contato': contato, 
                        'CNPJ': cnpj, 
                        'Email': email
                    }, auth_manager.get_user())
                    st.session_state['show_create_lead_modal'] = False
                    st.rerun()
        if st.button("CANCELAR CADASTRO", use_container_width=True):
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
        h1.subheader(f"📄 Gestão do Processo: {p['Razao_Social']} (#{p['ID_Lead']})")
        if h2.button("✖️", key=f"close_{lead_id}"):
            st.session_state['show_fullscreen_details'] = False
            st.rerun()

        # --- GESTÃO DE FLUXO (COM OPÇÃO DE VOLTAR) ---
        st.write("### ⚙️ Movimentação de Etapa")
        col_act1, col_act2, col_act3 = st.columns(3)
        stages = ETAPAS_KANBAN
        curr_idx = stages.index(p['Etapa_Atual'])
        
        # Botão VOLTAR (Bloqueado em Leads e Ganhos/Perdidos)
        if curr_idx > 0 and p['Etapa_Atual'] not in ['Ganhos', 'Perdidos']:
            if col_act1.button(f"⬅️ Recuar para {stages[curr_idx-1]}", use_container_width=True):
                repository.update_lead(lead_id, {'Etapa_Atual': stages[curr_idx-1]}, auth_manager.get_user(), f"Processo recuado para {stages[curr_idx-1]}")
                st.rerun()
        
        # Botão AVANÇAR (Bloqueado em Ganhos/Perdidos)
        if curr_idx < len(stages) - 1 and p['Etapa_Atual'] not in ['Ganhos', 'Perdidos']:
            if col_act2.button(f"➡️ Avançar para {stages[curr_idx+1]}", use_container_width=True, type="primary"):
                repository.update_lead(lead_id, {'Etapa_Atual': stages[curr_idx+1]}, auth_manager.get_user(), f"Processo avançado para {stages[curr_idx+1]}")
                st.rerun()
        
        # ATALHOS FINAIS
        with col_act3:
            ga, pe = st.columns(2)
            if ga.button("🏆 GANHO", use_container_width=True):
                repository.update_lead(lead_id, {'Etapa_Atual': 'Ganhos'}, auth_manager.get_user(), "🎯 VENDA CONCLUÍDA")
                st.rerun()
            if pe.button("📉 PERDIDO", use_container_width=True):
                repository.update_lead(lead_id, {'Etapa_Atual': 'Perdidos'}, auth_manager.get_user(), "❌ PROCESSO ENCERRADO")
                st.rerun()

        st.divider()

        # --- TABS DE INFORMAÇÃO ---
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Dados & Tags", "✅ Checklist", "📂 Arquivos", "📜 Histórico"])
        
        with tab1:
            c1, c2 = st.columns(2)
            with c1:
                new_razao = st.text_input("Razão Social", p['Razao_Social'])
                new_tel = st.text_input("Telefone", p['Telefone'])
                new_email = st.text_input("Email", p['Email'])
                new_nucleo = st.selectbox("Núcleo Responsável", NUCLEOS, index=NUCLEOS.index(p['Nucleo']) if p['Nucleo'] in NUCLEOS else 0)
            with c2:
                new_prio = st.selectbox("Prioridade", TAGS_PRIORIDADE, index=TAGS_PRIORIDADE.index(p['Prioridade']) if p['Prioridade'] in TAGS_PRIORIDADE else 1)
                new_risco = st.selectbox("Risco do Negócio", TAGS_RISCO, index=TAGS_RISCO.index(p['Risco']) if p['Risco'] in TAGS_RISCO else 0)
                new_esforco = st.selectbox("Esforço Necessário", TAGS_ESFORCO, index=TAGS_ESFORCO.index(p['Esforco']) if p['Esforco'] in TAGS_ESFORCO else 0)
                new_prazo = st.date_input("Próximo Retorno (Prazo)", value=pd.to_datetime(p['Prazo']).date() if pd.notna(p['Prazo']) else None)
            
            new_desc = st.text_area("Descrição Detalhada (Editável)", p['Descricao'], height=150)
            
            if st.button("SALVAR TODAS AS ALTERAÇÕES", type="primary", use_container_width=True):
                repository.update_lead(lead_id, {
                    'Razao_Social': new_razao, 'Telefone': new_tel, 'Email': new_email,
                    'Nucleo': new_nucleo, 'Prioridade': new_prio, 'Risco': new_risco,
                    'Esforco': new_esforco, 'Prazo': new_prazo, 'Descricao': new_desc
                }, auth_manager.get_user())
                st.rerun()

        with tab2:
            st.write("### ✅ Atividades Pendentes")
            items = json.loads(p['Checklist']) if p['Checklist'] and p['Checklist'] != "" else []
            new_item = st.text_input("Adicionar nova tarefa...")
            if st.button("Adicionar à Lista"):
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
                st.write("### 📂 Gestão de Documentos")
                up = st.file_uploader("Subir novo arquivo para o Drive", key=f"up_{lead_id}")
                if up:
                    anexos_manager.attach_file('Lead', lead_id, p['Razao_Social'], up, "Anexo Operacional", auth_manager.get_user())
                    st.rerun()
            else: st.info("ℹ️ Arquivos não são obrigatórios para leads em Ganhos ou Perdidos.")

        with tab4:
            st.write("### 💬 Central de Notas (Data + Usuário)")
            with st.form(f"comment_{lead_id}"):
                msg = st.text_area("Nova nota...")
                if st.form_submit_button("POSTAR NOTA"):
                    repository.add_comment_to_lead_history(lead_id, auth_manager.get_user(), msg)
                    st.rerun()
            
            hist = repository.get_all('Historico')
            if not hist.empty:
                hist['ID_Lead_Clean'] = pd.to_numeric(hist['ID_Lead'], errors='coerce')
                hist = hist[hist['ID_Lead_Clean'] == int(lead_id)].sort_values('Timestamp', ascending=False)
            
            c_com, c_sys = st.columns(2)
            with c_com:
                st.write("**📝 Notas Internas**")
                for _, r in hist[hist['Tipo'] == 'Comentário'].iterrows():
                    st.info(f"👤 {r['Usuario']} | 📅 {pd.to_datetime(r['Timestamp']).strftime('%d/%m %H:%M')}\n\n{r['Mensagem']}")
            with c_sys:
                st.write("**⚙️ Logs de Processo**")
                for _, r in hist[hist['Tipo'] == 'Ação'].iterrows():
                    st.caption(f"🕒 {pd.to_datetime(r['Timestamp']).strftime('%d/%m %H:%M')} - Alterou {r['Campo']}")

def display():
    st.markdown("""
        <style>
            /* Container das Colunas (Lanes) */
            [data-testid="stHorizontalBlock"] { 
                flex-wrap: nowrap !important; 
                overflow-x: auto !important; 
                gap: 1rem !important; 
                padding: 10px 5px !important; 
            }
            
            /* Estilização da "Pista" (Lane) do Kanban */
            .kanban-lane {
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 12px;
                padding: 15px;
                min-width: 400px;
                height: 100%;
            }

            /* Título da Coluna */
            .lane-title {
                color: #004a99;
                font-weight: bold;
                font-size: 1.2rem;
                text-align: center;
                border-bottom: 2px solid #004a99;
                padding-bottom: 10px;
                margin-bottom: 20px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }

            /* Card Styling */
            .stButton > button[key^="card_btn_"] { 
                height: auto !important; 
                padding: 15px !important; 
                text-align: left !important; 
                display: block !important; 
                border-radius: 10px !important; 
                border: 1px solid rgba(0,74,153,0.15) !important; 
                background-color: white !important; 
                transition: 0.2s !important; 
                line-height: 1.4 !important;
                margin-bottom: 10px !important;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
            }
            
            .stButton > button[key^="card_btn_"]:hover { 
                border-color: #004a99 !important; 
                box-shadow: 0 4px 12px rgba(0,74,153,0.1) !important; 
                transform: translateY(-2px) !important; 
                background-color: #f0f7ff !important;
            }

            .stButton > button[key^="card_btn_"] div p { 
                white-space: pre-wrap !important; 
                word-wrap: break-word !important; 
                font-size: 0.9rem !important;
            }
            
            /* Ajuste de largura mínima das colunas do Streamlit para o scroll horizontal */
            [data-testid="column"] {
                min-width: 1024px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # Cabeçalho da Página (fora das colunas estilizadas)
    head_col1, head_col2 = st.columns([7, 3])
    with head_col1:
        st.title("🎯 Fluxo de Operações")
    with head_col2:
        sort_order = st.selectbox("Ordenar por:", ["Mais Recentes", "Mais Antigos"])
        if st.button("＋ NOVO LEAD", use_container_width=True, type="primary"):
            st.session_state['show_create_lead_modal'] = True
            st.rerun()

    if st.session_state.get('show_create_lead_modal'): _display_create_lead_form()
    if st.session_state.get('show_fullscreen_details'): _display_lead_details_modal(st.session_state['selected_lead_id'])

    all_leads = repository.get_detailed_leads(sort_order)
    
    # Renderização das Colunas do Kanban
    cols = st.columns(len(ETAPAS_KANBAN))
    
    for i, etapa in enumerate(ETAPAS_KANBAN):
        with cols[i]:
            # Container com borda para criar a "Lane"
            with st.container(border=True):
                st.markdown(f"<div class='lane-title'>{etapa}</div>", unsafe_allow_html=True)
                
                etapa_leads = all_leads[all_leads['Etapa_Atual'] == etapa]
                
                if etapa_leads.empty:
                    st.caption("Nenhum item nesta etapa.")
                
                for _, p in etapa_leads.iterrows():
                    dias = (datetime.now() - pd.to_datetime(p['Data_Entrada_Etapa'])).days if pd.notna(p.get('Data_Entrada_Etapa')) else 0
                    criado = pd.to_datetime(p['Data_Criacao']).strftime('%d/%m/%y') if pd.notna(p['Data_Criacao']) else "N/A"
                    retorno = pd.to_datetime(p['Prazo']).strftime('%d/%m/%y') if pd.notna(p['Prazo']) else "Sem data"
                    
                    label_text = (
                        f"🏢 **{p['Razao_Social']}**\n\n"
                        f"📞 {p['Telefone']} | 👤 {p['Nome_Contato']}\n\n"
                        f"📅 Cadastrado em: {criado} ({dias}d na fase)\n\n"
                        f"⏳ Próximo Retorno: {retorno}\n"
                        f"────────────────────\n"
                        f"💬 {p.get('Ultimo_Comentario', 'Sem notas')}"
                    )
                    
                    # Card do Lead
                    if st.button(label_text, key=f"card_btn_{p['ID_Lead']}", use_container_width=True):
                        st.session_state['selected_lead_id'] = p['ID_Lead']
                        st.session_state['show_fullscreen_details'] = True
                        st.rerun()
                    
                    # Ações rápidas do Card
                    with st.popover("💬 Nota Rápida", use_container_width=True):
                        quick_note = st.text_area("Escreva sua nota...", key=f"quick_note_{p['ID_Lead']}")
                        if st.button("Salvar Nota", key=f"btn_save_{p['ID_Lead']}", type="primary"):
                            if quick_note:
                                repository.add_comment_to_lead_history(p['ID_Lead'], auth_manager.get_user(), quick_note)
                                st.rerun()
