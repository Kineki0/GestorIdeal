# app.py
import streamlit as st
import pandas as pd
import time
from services import auth_manager, assistant_manager
from views import kanban_view, dashboard_view, calendar_view, admin_clientes_view, admin_servicos_view, admin_kanban_view, admin_jarvis_brain_view
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
                ["Nenhum", "Gerenciar Clientes", "Gerenciar Serviços", "Gerenciar Kanban", "Treinar Jarvis"],
                label_visibility="collapsed"
            )

        st.divider()
        # O botão manual foi removido conforme solicitado, agora é automático.
            
        # --- ASSISTENTE JARVIS ---
        st.subheader("🤖 Assistente Jarvis")
        with st.expander("💬 Dúvida rápida?", expanded=False):
            # Botões de atalho rápido
            c1, c2 = st.columns(2)
            if c1.button("❓ Ajuda", use_container_width=True):
                st.session_state.last_jarvis_res = assistant_manager.ask_jarvis("ajuda")
                st.rerun()
            if c2.button("📖 Tutoriais", use_container_width=True):
                st.session_state.last_jarvis_res = assistant_manager.ask_jarvis("tutorial")
                st.rerun()
            if st.button("⚠️ Por que o alerta amarela?", use_container_width=True):
                st.session_state.last_jarvis_res = assistant_manager.ask_jarvis("aging")
                st.rerun()
            
            st.divider()
            
            if "assistant_reset" not in st.session_state:
                st.session_state.assistant_reset = 0
            
            q_key = f"jarvis_q_{st.session_state.assistant_reset}"
            user_q = st.text_input("Ou digite sua dúvida:", key=q_key)
            
            if st.button("🚀 PERGUNTAR", use_container_width=True):
                if user_q:
                    st.session_state.last_query = user_q # Salva a pergunta
                    res = assistant_manager.ask_jarvis(user_q)
                    st.session_state.last_jarvis_res = res
                    st.session_state.assistant_reset += 1
                    st.rerun()
            
            if "last_jarvis_res" in st.session_state:
                st.info(st.session_state.last_jarvis_res)
                
                # MECANISMO DE FEEDBACK
                st.write("Essa resposta ajudou?")
                fb_col1, fb_col2, fb_col3 = st.columns([1, 1, 2])
                
                if fb_col1.button("👍 Sim", key="fb_yes"):
                    st.toast("Obrigado! Fico feliz em ajudar.", icon="😊")
                    del st.session_state.last_jarvis_res
                    st.rerun()
                
                if fb_col2.button("👎 Não", key="fb_no"):
                    st.session_state.show_suggestion_field = True
                
                if st.session_state.get("show_suggestion_field"):
                    st.write("---")
                    st.caption("Como eu deveria ter respondido?")
                    suggestion = st.text_area("Sua sugestão de resposta:", key="sug_text")
                    if st.button("Enviar Sugestão", use_container_width=True):
                        if suggestion:
                            # Tenta extrair uma palavra-chave da última pergunta
                            repository.suggest_knowledge(st.session_state.get("last_query", "geral"), suggestion, user['Nome'])
                            st.success("Obrigado! Minha equipe vai analisar sua sugestão.")
                            time.sleep(2)
                            del st.session_state.last_jarvis_res
                            st.session_state.show_suggestion_field = False
                            st.rerun()

                if fb_col3.button("Limpar", type="secondary"):
                    del st.session_state.last_jarvis_res
                    if "show_suggestion_field" in st.session_state: del st.session_state.show_suggestion_field
                    st.rerun()

        if st.button("Logout", type="primary", use_container_width=True):
            auth_manager.logout()

    # Roteamento de página
    if admin_page and admin_page != "Nenhum":
        if admin_page == "Gerenciar Clientes":
            admin_clientes_view.display()
        elif admin_page == "Gerenciar Serviços":
            admin_servicos_view.display()
        elif admin_page == "Gerenciar Kanban":
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
