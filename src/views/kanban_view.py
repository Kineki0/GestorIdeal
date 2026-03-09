# kanban_view.py
import streamlit as st
import pandas as pd
import json
import re
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
            razao = c1.text_input("Razão Social *", placeholder="Ex: Empresa Exemplo LTDA")
            telefone = c1.text_input("Telefone (WhatsApp) *", placeholder="Ex: 11999998888")
            contato = c2.text_input("Nome do Contato *", placeholder="Ex: João Silva")
            cnpj = c2.text_input("CNPJ *", placeholder="Apenas números (14 dígitos)")
            email = st.text_input("Email (Opcional)", placeholder="exemplo@email.com")
            
            st.info("💡 Prazo e Observações serão definidos na etapa 'Em Progresso'.")
            
            if st.form_submit_button("CADASTRAR NO SISTEMA", use_container_width=True, type="primary"):
                # 1. LIMPEZA DE DADOS
                tel_clean = re.sub(r'\D', '', telefone)
                cnpj_clean = re.sub(r'\D', '', cnpj)
                
                # 2. VALIDAÇÕES
                errors = []
                if not razao or not telefone or not contato or not cnpj:
                    errors.append("❌ Razão Social, Telefone, Contato e CNPJ são OBRIGATÓRIOS.")
                
                if tel_clean and len(tel_clean) not in [8, 9, 10, 11]:
                    errors.append("❌ TELEFONE inválido. Deve ter 8 ou 9 dígitos (com ou sem DDD).")
                
                if cnpj_clean and len(cnpj_clean) != 14:
                    errors.append("❌ CNPJ inválido. Deve conter exatamente 14 dígitos numéricos.")
                
                if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                    errors.append("❌ FORMATO DE EMAIL inválido.")

                # 3. PROCESSAMENTO
                if errors:
                    for err in errors: st.error(err)
                else:
                    repository.create_lead({
                        'Razao_Social': razao, 
                        'Telefone': tel_clean, # Salva apenas números
                        'Nome_Contato': contato, 
                        'CNPJ': cnpj_clean, # Salva apenas números
                        'Email': email
                    }, auth_manager.get_user())
                    st.session_state['show_create_lead_modal'] = False
                    st.toast("✅ Lead cadastrado com sucesso!", icon="🚀")
                    st.rerun(scope="fragment")
        if st.button("CANCELAR CADASTRO", use_container_width=True):
            st.session_state['show_create_lead_modal'] = False
            st.rerun(scope="fragment")

@st.fragment
def _display_lead_details_modal(lead_id):
    if not st.session_state.get('show_fullscreen_details', False): return
    all_leads = repository.get_detailed_leads()
    p_filter = all_leads[all_leads['ID_Lead'].astype(int) == int(lead_id)]
    if p_filter.empty: return
    p = p_filter.iloc[0]
    
    stages = repository.get_kanban_stages()
    
    with st.container(border=True):
        h1, h2 = st.columns([15, 1])
        h1.subheader(f"📄 Gestão: {p['Razao_Social']} (#{p['ID_Lead']})")
        if h2.button("✖️", key=f"close_{lead_id}", use_container_width=True):
            st.session_state['show_fullscreen_details'] = False
            st.rerun(scope="fragment")

        # --- ÁREA ADMINISTRATIVA ---
        user_profile = auth_manager.get_user().get('Perfil', 'Usuário')
        if user_profile == 'Admin':
            with st.expander("⚠️ ÁREA ADMINISTRATIVA", expanded=False):
                if st.button("🗑️ EXCLUIR LEAD PERMANENTEMENTE", type="secondary", use_container_width=True):
                    repository.delete_lead(lead_id)
                    st.session_state['show_fullscreen_details'] = False
                    st.toast("🚨 Lead excluído.", icon="🗑️")
                    st.rerun(scope="fragment")
        
        st.divider()
        
        # --- BOTÕES DE AÇÃO ---
        current_stages = repository.get_kanban_stages()
        if p['Etapa_Atual'] in current_stages:
            curr_idx = current_stages.index(p['Etapa_Atual'])
        else:
            curr_idx = 0 
        
        # 1. Ação Principal: AVANÇAR
        if curr_idx < len(current_stages) - 1 and p['Etapa_Atual'] not in ['Ganhos', 'Perdidos']:
            target_stage = current_stages[curr_idx+1]
            if st.button(f"➡️ AVANÇAR PARA: {target_stage}", use_container_width=True, type="primary"):
                repository.update_lead(lead_id, {'Etapa_Atual': target_stage}, auth_manager.get_user(), f"Avançado para {target_stage}")
                st.rerun(scope="fragment")
        
        # 2. Ação Secundária: RECUAR
        if curr_idx > 0 and p['Etapa_Atual'] not in ['Ganhos', 'Perdidos']:
            target_stage = current_stages[curr_idx-1]
            if st.button(f"⬅️ RECUAR PARA: {target_stage}", use_container_width=True):
                repository.update_lead(lead_id, {'Etapa_Atual': target_stage}, auth_manager.get_user(), f"Recuado para {target_stage}")
                st.rerun(scope="fragment")
        
        col_f1, col_f2 = st.columns(2)
        if col_f1.button("🏆 GANHO", use_container_width=True):
            repository.update_lead(lead_id, {'Etapa_Atual': 'Ganhos'}, auth_manager.get_user(), "🎯 VENDA CONCLUÍDA")
            st.rerun(scope="fragment")
        if col_f2.button("📉 PERDIDO", use_container_width=True):
            repository.update_lead(lead_id, {'Etapa_Atual': 'Perdidos'}, auth_manager.get_user(), "❌ PROCESSO ENCERRADO")
            st.rerun(scope="fragment")

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
            
            new_desc = st.text_area("Descrição Detalhada (Editável)", value=p['Descricao'], height=150)
            
            if st.button("SALVAR TODAS AS ALTERAÇÕES", type="primary", use_container_width=True, key=f"save_all_{lead_id}"):
                repository.update_lead(lead_id, {
                    'Razao_Social': new_razao, 'Telefone': new_tel, 'Email': new_email,
                    'Nucleo': new_nucleo, 'Prioridade': new_prio, 'Risco': new_risco,
                    'Esforco': new_esforco, 'Prazo': new_prazo, 'Descricao': new_desc
                }, auth_manager.get_user())
                st.session_state['show_fullscreen_details'] = False
                st.rerun(scope="fragment")

        with tab2:
            st.write("### ✅ Atividades Pendentes")
            items = json.loads(p['Checklist']) if p['Checklist'] and p['Checklist'] != "" else []
            
            if items:
                done = sum(1 for item in items if item['done'])
                pending = len(items) - done
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.metric("Progresso Geral", f"{(done/len(items)*100):.0f}%")
                    st.write(f"📊 {done} de {len(items)} concluídas")
                with c2:
                    st.plotly_chart({
                        "data": [{"labels": ["Concluído", "Pendente"], "values": [done, pending], "type": "pie", "marker": {"colors": ["#004a99", "#e9ecef"]}, "hole": 0.4}],
                        "layout": {"margin": {"t": 0, "b": 0, "l": 0, "r": 0}, "height": 200, "showlegend": True}
                    }, use_container_width=True)
                st.divider()

            if f"chk_reset_{lead_id}" not in st.session_state:
                st.session_state[f"chk_reset_{lead_id}"] = 0
            
            chk_input_key = f"new_task_{lead_id}_{st.session_state[f'chk_reset_{lead_id}']}"
            new_item = st.text_input("Adicionar nova tarefa...", key=chk_input_key)
            
            if st.button("Adicionar à Lista", use_container_width=True, type="primary"):
                if new_item:
                    items.append({"task": new_item, "done": False})
                    repository.update_lead(lead_id, {'Checklist': json.dumps(items)}, auth_manager.get_user())
                    st.session_state[f"chk_reset_{lead_id}"] += 1 
                    st.rerun(scope="fragment")
            
            st.write("---")
            for i, item in enumerate(items):
                col_c, col_t, col_d = st.columns([0.1, 0.8, 0.1])
                if col_c.checkbox("", value=item['done'], key=f"chk_{lead_id}_{i}") != item['done']:
                    items[i]['done'] = not item['done']
                    repository.update_lead(lead_id, {'Checklist': json.dumps(items)}, auth_manager.get_user())
                    st.rerun(scope="fragment")
                label = f"~~{item['task']}~~" if item['done'] else item['task']
                col_t.markdown(label)
                if col_d.button("❌", key=f"del_chk_{lead_id}_{i}"):
                    items.pop(i)
                    repository.update_lead(lead_id, {'Checklist': json.dumps(items)}, auth_manager.get_user())
                    st.rerun(scope="fragment")

        with tab3:
            st.write("### 📂 Gestão de Documentos (Lazy Loading)")
            # LAZY LOADING: Só busca no banco/drive se clicar nesta aba (implícito no Streamlit tabs)
            anexos = repository.get_anexos_by_referencia('Lead', lead_id)
            if not anexos.empty:
                for _, a in anexos.iterrows():
                    with st.container(border=True):
                        c_icon, c_info, c_link, c_del = st.columns([1, 5, 2, 2])
                        c_icon.write("📄")
                        c_info.write(f"**{a['Nome_Arquivo']}**\n\n🕒 {pd.to_datetime(a['Data_Envio']).strftime('%d/%m/%y %H:%M')}")
                        c_link.link_button("🔗 ABRIR", a['Link_Drive'], use_container_width=True)
                        if c_del.button("🗑️ EXCLUIR", key=f"del_anexo_{a['ID_Anexo']}", type="secondary", use_container_width=True):
                            repository.delete_anexo(a['ID_Anexo'])
                            st.rerun(scope="fragment")
            else:
                st.info("Nenhum arquivo anexado.")

            st.divider()
            if p['Etapa_Atual'] not in ['Ganhos', 'Perdidos']:
                st.write("#### 📤 Subir novo arquivo")
                if f"uploader_reset_{lead_id}" not in st.session_state:
                    st.session_state[f"uploader_reset_{lead_id}"] = 0
                up_key = f"uploader_{lead_id}_{st.session_state[f'uploader_reset_{lead_id}']}"
                up = st.file_uploader("Selecione um arquivo", key=up_key)
                if up:
                    with st.status("Fazendo upload..."):
                        success = anexos_manager.attach_file('Lead', lead_id, p['Razao_Social'], up, "Anexo Operacional", auth_manager.get_user())
                        if success:
                            st.session_state[f"uploader_reset_{lead_id}"] += 1
                            st.toast(f"✅ Arquivo enviado!")
                            st.rerun(scope="fragment")

        with tab4:
            st.write("### 📜 Timeline")
            with st.form(f"comment_{lead_id}", clear_on_submit=True):
                msg = st.text_area("Nova nota interna...")
                if st.form_submit_button("Postar", use_container_width=True, type="primary"):
                    if msg:
                        repository.add_comment_to_lead_history(lead_id, auth_manager.get_user(), msg)
                        st.rerun(scope="fragment")
            
            st.divider()
            hist = repository.get_all('Historico')
            if not hist.empty:
                hist['ID_Lead_Clean'] = pd.to_numeric(hist['ID_Lead'], errors='coerce')
                this_hist = hist[hist['ID_Lead_Clean'] == int(lead_id)].sort_values('Timestamp', ascending=False)
                for _, r in this_hist.iterrows():
                    ts = pd.to_datetime(r['Timestamp']).strftime('%d/%m/%y %H:%M')
                    if r['Tipo'] == 'Comentário':
                        with st.chat_message("user", avatar="👤"):
                            st.write(f"**{r['Usuario']}** | {ts}")
                            st.info(r['Mensagem'])
                    else:
                        with st.chat_message("assistant", avatar="⚙️"):
                            st.caption(f"🔧 **Sistema** | {ts}")
                            st.write(f"_{r['Usuario']}_: **{r['Campo']}**")
            else:
                st.info("Histórico vazio.")

def display():
    # --- SIDEBAR DE FILTROS ---
    st.sidebar.header("🔍 Filtros Avançados")
    search_query = st.sidebar.text_input("Buscar (Empresa ou CNPJ)", placeholder="Digite aqui...")
    filter_nucleo = st.sidebar.multiselect("Filtrar por Núcleo", NUCLEOS)
    filter_prioridade = st.sidebar.multiselect("Filtrar por Prioridade", TAGS_PRIORIDADE)
    
    st.sidebar.divider()
    st.sidebar.write("💡 **Dica:** O sistema alerta com ⚠️ leads parados há mais de 5 dias na mesma fase.")

    st.markdown("""
        <style>
            /* FORÇAR CONTAINER DAS COLUNAS A PERMITIR SCROLL HORIZONTAL */
            [data-testid="stHorizontalBlock"] { 
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: nowrap !important; 
                overflow-x: auto !important; 
                gap: 1.5rem !important; 
                padding: 20px 10px !important;
                width: 100% !important;
            }

            /* LARGURA DAS COLUNAS (Ajustado para 380px) */
            [data-testid="stHorizontalBlock"] > div, div[data-testid="column"] {
                width: 380px !important;
                flex: none !important;
                min-width: 380px !important;
            }
            
            /* Título da Coluna (Restaurando Identidade) */
            .lane-title {
                color: #004a99 !important;
                font-weight: bold !important;
                font-size: 1.1rem !important;
                text-align: center !important;
                border-bottom: 3px solid #004a99 !important;
                padding-bottom: 10px !important;
                margin-bottom: 20px !important;
                text-transform: uppercase !important;
                letter-spacing: 1px !important;
            }

            /* Estilização da Barra de Rolagem */
            [data-testid="stHorizontalBlock"]::-webkit-scrollbar {
                height: 10px;
            }
            [data-testid="stHorizontalBlock"]::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 10px;
            }
            [data-testid="stHorizontalBlock"]::-webkit-scrollbar-thumb {
                background: #004a99;
                border-radius: 10px;
            }

            /* Card Styling & Text Wrap */
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
                margin-bottom: 12px !important;
                box-shadow: 0 4px 6px rgba(0,0,0,0.04) !important;
            }

            /* Forçar quebra de linha para respeitar o \n do Python */
            .stButton > button[key^="card_btn_"] div p {
                white-space: pre-wrap !important;
                word-wrap: break-word !important;
                display: block !important;
            }
            
            .stButton > button[key^="card_btn_"]:hover { 
                border-color: #004a99 !important; 
                box-shadow: 0 6px 12px rgba(0,74,153,0.1) !important; 
                transform: translateY(-2px) !important; 
                background-color: #f8fbff !important;
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
            st.rerun(scope="fragment")

    if st.session_state.get('show_create_lead_modal'): _display_create_lead_form()
    if st.session_state.get('show_fullscreen_details'): _display_lead_details_modal(st.session_state['selected_lead_id'])

    all_leads = repository.get_detailed_leads(sort_order)
    
    # --- APLICAÇÃO DOS FILTROS ---
    if search_query:
        # Garante que as colunas sejam tratadas como string para a busca
        mask = all_leads['Razao_Social'].astype(str).str.contains(search_query, case=False, na=False) | \
               all_leads['CNPJ'].astype(str).str.contains(search_query, na=False)
        all_leads = all_leads[mask]
    
    if filter_nucleo:
        all_leads = all_leads[all_leads['Nucleo'].isin(filter_nucleo)]
    
    if filter_prioridade:
        all_leads = all_leads[all_leads['Prioridade'].isin(filter_prioridade)]
    
    # Renderização das Colunas do Kanban
    current_stages = repository.get_kanban_stages()
    cols = st.columns(len(current_stages))
    
    for i, etapa in enumerate(current_stages):
        with cols[i]:
            # Container com borda para criar a "Lane"
            with st.container(border=True):
                st.markdown(f"<div class='lane-title'>{etapa}</div>", unsafe_allow_html=True)
                
                etapa_leads = all_leads[all_leads['Etapa_Atual'] == etapa]
                
                if etapa_leads.empty:
                    st.caption("Nenhum item nesta etapa.")
                
                for _, p in etapa_leads.iterrows():
                    # Lógica de Aging (SLA)
                    dias_na_etapa = (datetime.now() - pd.to_datetime(p['Data_Entrada_Etapa'])).days if pd.notna(p.get('Data_Entrada_Etapa')) else 0
                    is_stagnated = dias_na_etapa >= 5 and etapa not in ['Ganhos', 'Perdidos']
                    
                    criado = pd.to_datetime(p['Data_Criacao']).strftime('%d/%m/%y') if pd.notna(p['Data_Criacao']) else "N/A"
                    retorno = pd.to_datetime(p['Prazo']).strftime('%d/%m/%y') if pd.notna(p['Prazo']) else "Sem data"
                    
                    # Alerta visual no card
                    aging_warning = " ⚠️ **ESTAGNADO**" if is_stagnated else ""
                    
                    label_text = (
                        f"🏢 **{p['Razao_Social']}**{aging_warning}\n\n"
                        f"📞 {p['Telefone']} | 👤 {p['Nome_Contato']}\n\n"
                        f"📅 Cadastrado em: {criado} ({dias_na_etapa}d na fase)\n\n"
                        f"⏳ Próximo Retorno: {retorno}\n"
                        f"────────────────────\n\n"
                        f"💬 {p.get('Ultimo_Comentario', 'Sem notas')}"
                    )
                    
                    # Card do Lead (Aplica classe de aging se necessário)
                    if st.button(label_text, key=f"card_btn_{p['ID_Lead']}", use_container_width=True):
                        st.session_state['selected_lead_id'] = p['ID_Lead']
                        st.session_state['show_fullscreen_details'] = True
                        st.rerun(scope="fragment")
                    
                    # Ações rápidas do Card
                    with st.popover("💬 Nota Rápida", use_container_width=True):
                        quick_note = st.text_area("Escreva sua nota...", key=f"quick_note_{p['ID_Lead']}")
                        if st.button("Salvar Nota", key=f"btn_save_{p['ID_Lead']}", type="primary"):
                            if quick_note:
                                repository.add_comment_to_lead_history(p['ID_Lead'], auth_manager.get_user(), quick_note)
                                st.rerun(scope="fragment")
