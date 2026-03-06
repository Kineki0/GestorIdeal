# app.py
import streamlit as st
import pandas as pd
import time
from services import auth_manager
from views import kanban_view, dashboard_view, calendar_view, admin_clientes_view, admin_servicos_view, admin_kanban_view, admin_jarvis_brain_view, floating_assistant
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

    with st.sidebar:
        st.subheader(f"Bem-vindo(a), {user['Nome'].split(' ')[0]}!")
        st.write(f"Perfil: **{user['Perfil']}**")
        st.divider()

        # Menu de navegação principal
        page = st.radio(
            "Navegação",
            ["Kanban", "Dashboard", "Calendário"],
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

    # Roteamento de página
    if admin_page and admin_page != "Nenhum":
        if admin_page == "Gerenciar Kanban":
            admin_kanban_view.display()
        elif admin_page == "Treinar Jarvis":
            admin_jarvis_brain_view.display()
    else:
        if page == "Kanban":
            kanban_view.display()
        elif page == "Dashboard":
            dashboard_view.display()
        elif page == "Calendário":
            calendar_view.display()
        else:
            st.error("Página não encontrada.")

if __name__ == "__main__":
    main()
