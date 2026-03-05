# kanban_view.py
import streamlit as st
import pandas as pd
from datetime import datetime
from data import repository_excel as repository
from services import auth_manager, historico_manager, anexos_manager
from config import TAGS_PROCESSO

def _display_create_lead_form():
    """Exibe o formulário de criação de lead no topo."""
    if not st.session_state.get('show_create_lead_modal', False):
        return
    etapa = st.session_state.get('create_lead_etapa', "")
    with st.container(border=True):
        st.subheader(f"🚀 Novo Lead - {etapa}")
        with st.form("form_create_final_v21", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                razao = st.text_input("Razão Social")
                fantasia = st.text_input("Nome Fantasia")
                contato = st.text_input("Contato")
                email = st.text_input("Email")
            with c2:
                cnpj = st.text_input("CNPJ")
                prioridade = st.selectbox("Prioridade", ["Baixa", "Média", "Alta"], index=1)
                prazo = st.date_input("Prazo", value=None)
                desc = st.text_area("Observações")
            
            btn_c1, btn_c2 = st.columns(2)
            if btn_c1.form_submit_button("✅ SALVAR", use_container_width=True, type="primary"):
                # Validação de campos obrigatórios
                if not razao or not contato or not email:
                    st.error("⚠️ Por favor, preencha os campos obrigatórios: Razão Social, Contato e Email.")
                else:
                    repository.create_lead({
                        'Descricao': desc, 'Nome_Contato': contato, 'CNPJ': cnpj, 
                        'Email': email, 'Razao_Social': razao, 'Nome_Fantasia': fantasia, 
                        'Prazo': prazo, 'Prioridade': prioridade, 'etapa_inicial': etapa
                    }, auth_manager.get_user())
                    st.session_state['show_create_lead_modal'] = False
                    st.rerun()

            if btn_c2.form_submit_button("CANCELAR", use_container_width=True):
                st.session_state['show_create_lead_modal'] = False
                st.rerun()

def _display_lead_details_modal(lead_id):
    """Exibe os detalhes COMPLETOS do lead."""
    if not st.session_state.get('show_fullscreen_details', False):
        return

    all_leads = repository.get_detailed_leads()
    try:
        p = all_leads[all_leads['ID_Lead'].astype(int) == int(lead_id)].iloc[0]
    except Exception:
        st.error("Lead não encontrado.")
        return

    with st.container(border=True):
        head_c1, head_c2 = st.columns([9, 1])
        head_c1.subheader(f"📋 Lead #{p['ID_Lead']} - {p.get('Nome_Contato', 'N/A')}")
        
        from services import pdf_manager
        pdf_bytes = pdf_manager.generate_lead_pdf(p)
        st.download_button(
            label="📄 Baixar Ficha PDF",
            data=pdf_bytes,
            file_name=f"Lead_{p['ID_Lead']}.pdf",
            mime="application/pdf",
            key=f"pdf_{lead_id}"
        )

        if head_c2.button("✖️", key=f"close_det_{lead_id}"):
            st.session_state['show_fullscreen_details'] = False
            st.rerun()

        st.write("**Ações de Fluxo**")
        act_c1, act_c2, act_c3 = st.columns(3)
        if act_c1.button("➡️ Próxima Etapa", key=f"nxt_{lead_id}", use_container_width=True, type="primary"):
            stages = repository.get_kanban_stages()
            curr_idx = stages.index(p['Etapa_Atual'])
            if curr_idx < len(stages) - 1:
                repository.update_lead(lead_id, {'Etapa_Atual': stages[curr_idx+1]}, auth_manager.get_user(), f"Movido para {stages[curr_idx+1]}")
                st.rerun()
        if act_c2.button("✅ Concluir", key=f"dn_{lead_id}", use_container_width=True, type="primary"):
            repository.update_lead(lead_id, {'Etapa_Atual': 'Concluído'}, auth_manager.get_user(), "Concluído")
            st.rerun()
        if act_c3.button("❌ Cancelar Lead", key=f"cnl_{lead_id}", use_container_width=True, type="primary"):
            repository.update_lead(lead_id, {'Etapa_Atual': 'Cancelado'}, auth_manager.get_user(), "Cancelado")
            st.rerun()

        st.divider()
        col_inf1, col_inf2 = st.columns(2)
        with col_inf1:
            st.write(f"**Razão Social:** {p.get('Razao_Social', 'N/A')}")
            st.write(f"**CNPJ:** {p.get('CNPJ', 'N/A')}")
            st.write(f"**E-mail:** {p.get('Email', 'N/A')}")
        with col_inf2:
            st.write(f"**Prioridade:** {p.get('Prioridade', 'N/A')}")
            st.write(f"**Etapa Atual:** {p.get('Etapa_Atual', 'N/A')}")
            st.write(f"**Prazo:** {p['Prazo'].strftime('%d/%m/%Y') if pd.notna(p['Prazo']) else 'N/A'}")
            
            valid_tags = [t.strip() for t in str(p.get('Tags', '')).split(',') if t.strip() in TAGS_PROCESSO]
            tags = st.multiselect("Tags", TAGS_PROCESSO, default=valid_tags, key=f"tgs_{lead_id}")
            if st.button("Salvar Tags", key=f"btgs_{lead_id}", type="primary"):
                repository.update_lead(lead_id, {"Tags": ",".join(tags)}, auth_manager.get_user())
                st.rerun()

        st.write(f"**Descrição:** {p.get('Descricao', 'N/A')}")
        st.divider()
        st.write("📂 **Anexos (Drive)**")
        anexos = repository.get_anexos_by_referencia('Lead', lead_id)
        for _, a in anexos.iterrows(): st.markdown(f"- [{a['Nome_Arquivo']}]({a['Link_Drive']})")
        
        with st.expander("➕ Adicionar Anexo"):
            up_f = st.file_uploader("Arquivo", key=f"up_{lead_id}")
            up_d = st.text_input("Descrição", key=f"desc_{lead_id}")
            if st.button("Upload", key=f"fbtn_{lead_id}", type="primary"):
                if up_f and up_d:
                    if anexos_manager.attach_file('Lead', lead_id, p.get('Razao_Social', 'N/A'), up_f, up_d, auth_manager.get_user()):
                        st.rerun()

        st.divider()
        historico_manager.display_history_for_lead(lead_id)

def display():
    # Estados
    if 'dragged_lead_id' not in st.session_state: st.session_state.dragged_lead_id = None
    if 'show_create_lead_modal' not in st.session_state: st.session_state['show_create_lead_modal'] = False
    if 'show_add_stage_modal' not in st.session_state: st.session_state['show_add_stage_modal'] = False
    if 'show_bulk_delete' not in st.session_state: st.session_state['show_bulk_delete'] = False
    if 'show_rename_modal' not in st.session_state: st.session_state['show_rename_modal'] = False

    # CSS PADRONIZADO
    st.markdown("""
        <style>
            /* PADRONIZAÇÃO DE BOTÕES - FIM DO VERMELHO */
            .stButton > button[kind="primary"] {
                background-color: #004a99 !important;
                color: white !important;
                font-weight: bold !important;
                border: none !important;
            }
            .stButton > button[kind="primary"]:hover {
                background-color: #003366 !important;
                box-shadow: 0 4px 10px rgba(0,0,0,0.2) !important;
            }
            .stButton > button[kind="secondary"] {
                background-color: rgba(0, 74, 153, 0.08) !important;
                color: #004a99 !important;
                border: 1px solid rgba(0, 74, 153, 0.2) !important;
            }
            .stButton > button[kind="secondary"]:hover {
                background-color: rgba(0, 74, 153, 0.15) !important;
                border-color: #004a99 !important;
            }
            .stButton > button[key^="ed_btn_"], .stButton > button[key^="rm_btn_"] {
                background-color: transparent !important;
                border: none !important;
                color: #004a99 !important;
                box-shadow: none !important;
            }
            .stButton > button[key^="rm_btn_"] { color: #ff4b4b !important; }
            .stButton > button { border-radius: 8px !important; }
            
            [data-testid="stHorizontalBlock"] {
                flex-wrap: nowrap !important;
                overflow-x: auto !important;
                gap: 1.5rem !important;
                padding-bottom: 30px !important;
            }
            [data-testid="column"] { min-width: 380px !important; max-width: 380px !important; }
            .lead-card {
                background-color: var(--secondary-background-color);
                border: 1px solid rgba(128, 128, 128, 0.2);
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 8px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            }
            .lead-id { color: var(--text-color); font-weight: bold; font-size: 1rem; }
            .comment-box {
                background-color: rgba(128, 128, 128, 0.08);
                padding: 8px;
                font-size: 0.85rem;
                font-style: italic;
                margin-top: 10px;
                border-radius: 6px;
            }
            .sla-badge {
                font-size: 0.75rem;
                background-color: #004a99;
                color: white !important;
                padding: 2px 8px;
                border-radius: 10px;
                float: right;
                font-weight: bold;
            }
            .prio-alta { border-left: 6px solid #ff4b4b; }
            .prio-media { border-left: 6px solid #ffa500; }
            .prio-baixa { border-left: 6px solid #28a745; }

            /* Estilo para Checkboxes, Toggles e Radio Buttons (Azul Corporativo) */
            div[data-baseweb="checkbox"] div {
                background-color: #004a99 !important;
                border-color: #004a99 !important;
            }
            div[role="checkbox"][aria-checked="true"] {
                background-color: #004a99 !important;
            }
            /* Cor do Switch/Toggle */
            div[data-testid="stCheckbox"] > label > div:first-child > div {
                background-color: #004a99 !important;
            }
            /* Overrides específicos de classes Streamlit para remover o vermelho */
            .st-d9 {
                background-color: #004a99 !important;
            }
            /* Override para botões primários (estilo emotion cache) */
            .st-emotion-cache-1krtkoa {
                background-color: #004a99 !important;
                color: white !important;
                border: 1px solid #004a99 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # Header Principal
    st.markdown("<h1 style='color:white;'>🎯 Gestão de Leads</h1>", unsafe_allow_html=True)
    
    col_f1, col_f2, col_f3 = st.columns([5, 2, 3])
    with col_f1:
        search_term = st.text_input("🔍 Buscar Lead", placeholder="Digite nome, empresa ou CNPJ...")
    with col_f2:
        filter_prio = st.multiselect("Prioridade", ["Baixa", "Média", "Alta"])
    with col_f3:
        if auth_manager.has_permission(["Admin", "Operacional"]):
            c1, c2 = st.columns(2)
            if c1.button("➕ Nova Coluna", use_container_width=True, type="primary", key="btn_trigger_add_col"):
                st.session_state['show_add_stage_modal'] = True
                st.rerun()
            if c2.button("🗑️ Limpar Leads", use_container_width=True, type="primary", key="btn_trigger_bulk_del"):
                st.session_state['show_bulk_delete'] = not st.session_state.get('show_bulk_delete', False)
                st.rerun()

    # --- MODAIS E INTERFACES DE TOPO ---
    if st.session_state.get('show_add_stage_modal'):
        stages = repository.get_kanban_stages()
        with st.container(border=True):
            st.subheader("🚀 Adicionar Nova Coluna")
            n_name = st.text_input("Nome da Etapa")
            pos_options = ["No Início"] + [f"Depois de '{s}'" for s in stages]
            pos_sel = st.selectbox("Posição:", pos_options, index=len(pos_options)-1)
            b_c1, b_c2 = st.columns(2)
            if b_c1.button("CRIAR", type="primary", use_container_width=True):
                if n_name:
                    new_order = 0 if pos_sel == "No Início" else stages.index(pos_sel.replace("Depois de '", "").replace("'", "")) + 1
                    repository.add_kanban_stage(n_name, insert_at_order=new_order)
                    st.session_state['show_add_stage_modal'] = False
                    st.rerun()
            if b_c2.button("CANCELAR", use_container_width=True):
                st.session_state['show_add_stage_modal'] = False
                st.rerun()

    if st.session_state.get('show_rename_modal'):
        with st.container(border=True):
            old_name = st.session_state.get('old_stage_name', "")
            st.subheader(f"✏️ Renomear: {old_name}")
            new_name = st.text_input("Novo Nome", value=old_name)
            br1, br2 = st.columns(2)
            if br1.button("SALVAR", type="primary", use_container_width=True):
                if new_name and new_name != old_name:
                    repository.rename_kanban_stage(old_name, new_name)
                    st.session_state['show_rename_modal'] = False
                    st.rerun()
            if br2.button("FECHAR", use_container_width=True):
                st.session_state['show_rename_modal'] = False
                st.rerun()

    if st.session_state.get('show_bulk_delete'):
        all_leads = repository.get_detailed_leads()
        with st.container(border=True):
            st.subheader("🗑️ Painel de Exclusão em Massa")
            options = {f"#{r['ID_Lead']} - {r.get('Razao_Social') or 'N/A'}": r['ID_Lead'] for _, r in all_leads.iterrows()}
            sels = st.multiselect("Selecione os leads:", list(options.keys()))
            c_del1, c_del2 = st.columns(2)
            if c_del1.button("CONFIRMAR EXCLUSÃO", type="primary", use_container_width=True):
                if sels:
                    repository.delete_leads([options[x] for x in sels], auth_manager.get_user())
                    st.session_state['show_bulk_delete'] = False
                    st.rerun()
                else:
                    st.warning("Selecione ao menos um lead.")
            if c_del2.button("CANCELAR EXCLUSÃO", use_container_width=True):
                st.session_state['show_bulk_delete'] = False
                st.rerun()

    if st.session_state['show_create_lead_modal']: _display_create_lead_form()
    if st.session_state.get('show_fullscreen_details'): _display_lead_details_modal(st.session_state['selected_lead_id'])

    # Dados e Filtragem (novamente para garantir dados frescos após exclusão)
    all_leads = repository.get_detailed_leads()
    if search_term:
        term = search_term.lower()
        all_leads = all_leads[
            all_leads['Nome_Contato'].str.lower().str.contains(term, na=False) |
            all_leads['Razao_Social'].str.lower().str.contains(term, na=False) |
            all_leads['CNPJ'].astype(str).str.contains(term, na=False)
        ]
    if filter_prio:
        all_leads = all_leads[all_leads['Prioridade'].isin(filter_prio)]

    stages = repository.get_kanban_stages()
    tasks = {e: [] for e in stages}
    for _, p in all_leads.iterrows():
        if p['Etapa_Atual'] in tasks: tasks[p['Etapa_Atual']].append(p)

    cols = st.columns(len(stages))

    for i, etapa in enumerate(stages):
        with cols[i]:
            st.markdown(f"### {etapa}")
            if auth_manager.has_permission(["Admin", "Operacional"]):
                c_act1, c_act2 = st.columns(2)
                if c_act1.button("✏️ Editar", key=f"ed_btn_{etapa}", use_container_width=True):
                    st.session_state['old_stage_name'] = etapa
                    st.session_state['show_rename_modal'] = True
                    st.rerun()
                if c_act2.button("🗑️ Remover", key=f"rm_btn_{etapa}", use_container_width=True):
                    if repository.remove_kanban_stage(etapa): st.rerun()

            if st.button(f"＋ Adicionar Lead", key=f"add_btn_{etapa}", use_container_width=True, type="primary"):
                st.session_state['create_lead_etapa'] = etapa
                st.session_state['show_create_lead_modal'] = True
                st.rerun()

            for p in tasks[etapa]:
                prio = str(p.get('Prioridade', 'Média')).lower()
                prio_class = f"prio-{prio}" if prio in ['alta', 'media', 'baixa'] else "prio-media"
                dias = (datetime.now() - pd.to_datetime(p['Data_Entrada_Etapa'])).days if pd.notna(p.get('Data_Entrada_Etapa')) else 0
                
                with st.container():
                    st.markdown(f"""
                        <div class="lead-card {prio_class}">
                            <span class="sla-badge">{dias}d</span>
                            <div class="lead-id">#{p['ID_Lead']} - {p.get('Nome_Contato', 'N/A')}</div>
                            <div style="font-size:0.85rem; opacity:0.8; margin-top:3px;">{p.get('Razao_Social', 'N/A')}</div>
                            <div class="comment-box">💬 {p.get('Ultimo_Comentario', 'Sem notas')}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    _, bc1, bc2, bc3 = st.columns([0.1, 0.3, 0.3, 0.3])
                    with bc1:
                        if st.button("👁️", key=f"v_view_{p['ID_Lead']}", help="Detalhes"):
                            st.session_state['selected_lead_id'] = int(p['ID_Lead'])
                            st.session_state['show_fullscreen_details'] = True
                            st.rerun()
                    with bc2:
                        with st.popover("💬", help="Nota"):
                            nt = st.text_area("Nota", key=f"nt_note_{p['ID_Lead']}")
                            if st.button("OK", key=f"s_save_{p['ID_Lead']}", type="primary"):
                                repository.add_comment_to_lead_history(p['ID_Lead'], auth_manager.get_user(), nt)
                                st.rerun()
                    with bc3:
                        if st.button("➡️", key=f"m_move_{p['ID_Lead']}", help="Mover"):
                            st.session_state.dragged_lead_id = p['ID_Lead']
                            st.rerun()
