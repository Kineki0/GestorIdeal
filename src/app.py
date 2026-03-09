# app.py
import streamlit as st
import pandas as pd
import time
from datetime import datetime
from services import auth_manager
from views import kanban_view, kanban_mobile_view, dashboard_view, calendar_view, admin_clientes_view, admin_servicos_view, admin_kanban_view, admin_jarvis_brain_view, floating_assistant
from data import repository_excel as repository

# --- Configuração da Página ---
st.set_page_config(
    page_title="Gestor Ideal",
    page_icon="image-_57_.ico",
    layout="wide"
)

def main():
    """Função principal que atua como roteador da aplicação."""
    repository.init_session_state() # Inicializa o banco de dados na sessão

    # Verifica se o usuário está logado. Se não, exibe o formulário de login.
    if not auth_manager.is_logged_in():
        auth_manager.display_login_form()
        return

    # --- Se o usuário está logado, exibe a aplicação principal ---
    user = auth_manager.get_user()
    
    # Verifica conexão com o Google para habilitar sincronização
    from services import drive_manager
    st.session_state.google_authorized = drive_manager.check_drive_connection()
    
    # --- Configuração de Salvamento Automático ---
    if 'last_auto_save' not in st.session_state:
        st.session_state.last_auto_save = time.time()
    
    # Verifica se passaram 25 segundos desde o último salvamento
    current_time = time.time()
    if current_time - st.session_state.last_auto_save > 25:
        repository.commit_to_file()
        st.session_state.last_auto_save = current_time
        st.toast("💾 Alterações salvas automaticamente!", icon="✅")

    # --- Detecção de Dispositivo (Mobile vs Desktop) ---
    user_agent = st.context.headers.get("User-Agent", "")
    is_mobile = any(x in user_agent for x in ["Android", "iPhone", "iPad"])

    # --- Backup Automático Diário ---
    try:
        if st.session_state.google_authorized:
            hoje = datetime.now().date()
            last_date = st.session_state.get('last_backup_date')
            
            if last_date != hoje:
                from services import drive_manager
                if drive_manager.create_backup_snapshot():
                    st.session_state.last_backup_date = hoje
                    st.toast("🛡️ Backup de segurança realizado no Drive!", icon="☁️")
    except Exception:
        pass # Falha silenciosa para não travar o app principal

    with st.sidebar:
        st.subheader(f"Bem-vindo(a), {user['Nome'].split(' ')[0]}!")
        st.write(f"Perfil: **{user['Perfil']}**")
        st.divider()

        # Menu de navegação dinâmico baseado no dispositivo
        nav_options = ["Kanban Mobile 📱"] if is_mobile else ["Kanban"]
        nav_options += ["Dashboard", "Calendário"]

        page = st.radio(
            "Navegação",
            nav_options,
            label_visibility="collapsed"
        )
        
        # Menu de administração, visível apenas para Admins
        admin_page = None
        if auth_manager.has_permission(["Admin"]):
            st.divider()
            st.subheader("Administração")
            admin_page = st.radio(
                "Admin",
                ["Nenhum", "Gerenciar Kanban", "Treinar Jarvis"],
                label_visibility="collapsed"
            )

        st.divider()
        if st.button("Logout", type="primary", use_container_width=True):
            auth_manager.logout()

    # --- ASSISTENTE IDEAL (FLUTUANTE) ---
    floating_assistant.display_floating_assistant()

    # --- LÓGICA DE TRANSIÇÃO COM CARREGAMENTO ---
    import utils
    utils.apply_page_config()

    # Detecta mudança de página ou abertura de detalhes para mostrar loading
    current_nav = f"{page}_{admin_page}_{st.session_state.get('show_fullscreen_details', False)}_{st.session_state.get('selected_lead_id', '')}"
    
    if 'last_nav' not in st.session_state:
        st.session_state.last_nav = current_nav

    if st.session_state.last_nav != current_nav:
        # Se mudou algo na navegação, mostra a tela de carregamento
        loading_msg = "SINCROZINANDO DADOS..."
        if st.session_state.get('show_fullscreen_details'):
            loading_msg = "ABRINDO DETALHES DO PROCESSO..."
        elif page != st.session_state.last_nav.split('_')[0]:
            loading_msg = f"CARREGANDO {page.upper()}..."
            
        utils.loading_screen(loading_msg)
        st.session_state.last_nav = current_nav
        # Não damos rerun aqui pois o streamlit já está no meio do ciclo de renderização

    # Roteamento de página
    if admin_page and admin_page != "Nenhum":
        if admin_page == "Gerenciar Kanban":
            admin_kanban_view.display()
        elif admin_page == "Treinar Jarvis":
            admin_jarvis_brain_view.display()
    else:
        if page == "Kanban":
            kanban_view.display()
        elif page == "Kanban Mobile 📱":
            kanban_mobile_view.display()
        elif page == "Dashboard":
            dashboard_view.display()
        elif page == "Calendário":
            calendar_view.display()
        else:
            st.error("Página não encontrada.")

if __name__ == "__main__":
    main()
