# auth_manager.py
import streamlit as st
from data import repository_excel as repository
import utils
import config
from datetime import datetime, timedelta
import extra_streamlit_components as stx

def _get_cookie_manager():
    """Inicializa o gerenciador de cookies de forma persistente."""
    if 'cookie_manager' not in st.session_state:
        st.session_state.cookie_manager = stx.CookieManager()
    return st.session_state.cookie_manager

def login(email, password):
    """
    Autentica um usuário e o armazena na sessão e em um cookie.
    """
    if not email or not password:
        st.error("Por favor, insira email e senha.")
        return False

    user_data = repository.get_user_by_email(email)

    if user_data and user_data.get('Ativo', False) and utils.verify_password(password, user_data['Senha']):
        st.session_state['logged_in'] = True
        st.session_state['user'] = {
            "ID_Usuario": user_data['ID_Usuario'],
            "Nome": user_data['Nome'],
            "Email": user_data['Email'],
            "Perfil": user_data['Perfil']
        }
        
        # SALVA O LOGIN NOS COOKIES (Válido por 30 dias)
        cookie_manager = _get_cookie_manager()
        cookie_manager.set('gestor_ideal_user', email, expires_at=datetime.now() + timedelta(days=30))
        
        repository.log_system_event(f"Login bem-sucedido para o usuário: {email}", "INFO")
        return True
    else:
        repository.log_system_event(f"Tentativa de login falhou para o email: {email}", "AVISO")
        st.error("Email ou senha incorretos, ou usuário inativo.")
        return False

def logout():
    """
    Realiza o logout do usuário, limpando a sessão e os cookies.
    """
    if 'user' in st.session_state:
        repository.log_system_event(f"Logout do usuário: {st.session_state['user']['Email']}", "INFO")
        del st.session_state['user']
    st.session_state['logged_in'] = False
    
    # REMOVE O COOKIE
    cookie_manager = _get_cookie_manager()
    cookie_manager.delete('gestor_ideal_user')
    
    st.success("Logout realizado com sucesso!")
    st.rerun()

def get_user():
    """Retorna o usuário logado, se existir."""
    return st.session_state.get('user')

def is_logged_in():
    """Verifica se há um usuário logado na sessão ou nos cookies."""
    # 1. Verifica na sessão atual
    if st.session_state.get('logged_in', False):
        return True
    
    # 2. Tenta recuperar do cookie se não estiver na sessão
    cookie_manager = _get_cookie_manager()
    saved_email = cookie_manager.get('gestor_ideal_user')
    
    if saved_email:
        user_data = repository.get_user_by_email(saved_email)
        if user_data and user_data.get('Ativo', False):
            st.session_state['logged_in'] = True
            st.session_state['user'] = {
                "ID_Usuario": user_data['ID_Usuario'],
                "Nome": user_data['Nome'],
                "Email": user_data['Email'],
                "Perfil": user_data['Perfil']
            }
            return True
            
    return False

def has_permission(required_profiles):
    """
    Verifica se o perfil do usuário logado está na lista de perfis requeridos.
    """
    if not is_logged_in():
        return False
    
    user_data = get_user()
    if not user_data: return False
    
    user_profile = user_data.get('Perfil')
    return user_profile in required_profiles

def display_login_form():
    """
    Exibe o formulário de login na tela.
    """
    st.header("Ideal - Login")

    if st.session_state.get('show_registration_form', False):
        display_registration_form()
    elif st.session_state.get('show_forgot_password_form', False):
        display_forgot_password_form()
    elif st.session_state.get('show_reset_password_form', False):
        display_reset_password_form()
    else:
        with st.form("login_form"):
            email = st.text_input("Email").lower()
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")

            if submitted:
                if login(email, password):
                    st.rerun()

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Criar Nova Conta"):
                st.session_state['show_registration_form'] = True
                st.rerun()
        with col2:
            if st.button("Esqueci minha senha"):
                st.session_state['show_forgot_password_form'] = True
                st.rerun()

def display_registration_form():
    """
    Exibe o formulário de cadastro de novo usuário.
    """
    st.header("Ideal - Cadastro de Usuário")

    with st.form("registration_form"):
        name = st.text_input("Nome Completo")
        email = st.text_input("Email").lower()
        password = st.text_input("Senha", type="password")
        confirm_password = st.text_input("Confirmar Senha", type="password")
        
        profile_options = [profile_key for profile_key in config.PERFIS_USUARIO.keys() if profile_key != "Admin"]
        profile_display_map = {config.PERFIS_USUARIO[key]: key for key in profile_options}
        selected_profile_display = st.selectbox("Perfil", options=list(profile_display_map.keys()))
        profile = profile_display_map[selected_profile_display]

        submitted = st.form_submit_button("Cadastrar")

        if submitted:
            if not name or not email or not password or not confirm_password:
                st.error("Por favor, preencha todos os campos.")
            elif password != confirm_password:
                st.error("As senhas não coincidem.")
            elif repository.user_exists(email):
                st.error("Este email já está cadastrado.")
            else:
                hashed_password = utils.hash_password(password)
                new_user_id = repository.register_user(name, email, hashed_password, profile)
                if new_user_id:
                    st.success("Usuário cadastrado com sucesso! Faça login para continuar.")
                    st.session_state['show_registration_form'] = False
                    st.rerun()
                else:
                    st.error("Ocorreu um erro ao cadastrar o usuário.")

    if st.button("Voltar para o Login"):
        st.session_state['show_registration_form'] = False
        st.rerun()

from services import email_manager

def display_forgot_password_form():
    """
    Exibe o formulário para solicitação de reset de senha.
    """
    st.header("Ideal - Recuperar Senha")

    with st.form("forgot_password_form"):
        email = st.text_input("Digite seu email cadastrado").lower()
        submitted = st.form_submit_button("Gerar Link de Reset")

        if submitted:
            user_data = repository.get_user_by_email(email)
            if user_data:
                token = repository.create_password_reset_token(email)
                if email_manager.send_password_reset_email(email, token):
                    st.success(f"Um e-mail de recuperação foi enviado para {email}.")
                    st.session_state['reset_password_token'] = token 
                    st.session_state['show_forgot_password_form'] = False
                    st.session_state['show_reset_password_form'] = True
                    st.rerun()
                else:
                    st.error("Falha ao enviar e-mail. Verifique a conexão com o Google.")
            else:
                st.error("Email não encontrado.")

    if st.button("Voltar para o Login"):
        st.session_state['show_forgot_password_form'] = False
        st.rerun()

def display_reset_password_form():
    """
    Exibe o formulário para resetar a senha com o token recebido por e-mail.
    """
    st.header("Ideal - Definir Nova Senha")
    st.info("Insira o código enviado para o seu e-mail e escolha sua nova senha.")

    with st.form("reset_password_form"):
        input_token = st.text_input("Código de Verificação (Token)")
        new_password = st.text_input("Nova Senha", type="password")
        confirm_new_password = st.text_input("Confirmar Nova Senha", type="password")
        submitted = st.form_submit_button("Redefinir Senha")

        if submitted:
            if not input_token:
                st.error("Por favor, insira o código de verificação enviado por e-mail.")
            elif new_password != confirm_new_password:
                st.error("As novas senhas não coincidem.")
            elif len(new_password) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            else:
                token_record = repository.get_password_reset_token(input_token)
                if token_record:
                    hashed_password = utils.hash_password(new_password)
                    if repository.update_user_password(token_record['Email'], hashed_password):
                        repository.invalidate_password_reset_token(input_token)
                        st.success("Sua senha foi redefinida com sucesso! Faça login com a nova senha.")
                        st.session_state['show_reset_password_form'] = False
                        st.session_state['reset_password_token'] = ''
                        st.rerun()
                    else:
                        st.error("Ocorreu um erro ao atualizar a senha.")
                else:
                    st.error("Código de verificação inválido, expirado ou já utilizado.")

    if st.button("Voltar para o Login"):
        st.session_state['show_reset_password_form'] = False
        st.session_state['reset_password_token'] = ''
        st.rerun()
