# utils.py
import bcrypt
from datetime import datetime, timedelta
import pandas as pd
from config import INDICADORES_STATUS, DIAS_ALERTA_PRAZO

def apply_page_config():
    """Aplica configurações visuais e animações de transição."""
    import streamlit as st
    st.markdown("""
        <style>
            /* Animação de Fade-in para o conteúdo principal */
            .main .block-container {
                animation: fadeIn 0.8s ease-in-out;
            }
            @keyframes fadeIn {
                0% { opacity: 0; transform: translateY(20px); }
                100% { opacity: 1; transform: translateY(0); }
            }
            
            /* Estilização do Spinner para parecer o reator do Jarvis */
            div.stSpinner > div {
                border-top-color: #00d4ff !important;
                border-width: 4px !important;
                width: 60px !important;
                height: 60px !important;
                margin: auto;
            }
            
            /* Texto de carregamento pulsante */
            .loading-text {
                text-align: center;
                color: #00d4ff;
                font-family: 'monospace';
                font-weight: bold;
                letter-spacing: 2px;
                animation: pulse 1.5s infinite;
            }
            @keyframes pulse {
                0% { opacity: 0.4; }
                50% { opacity: 1; }
                100% { opacity: 0.4; }
            }
        </style>
    """, unsafe_allow_html=True)

def loading_screen(text="INICIALIZANDO JARVIS..."):
    """Exibe uma tela de carregamento padronizada e estilizada."""
    import streamlit as st
    st.markdown(f'<p class="loading-text">{text}</p>', unsafe_allow_html=True)
    return st.spinner("")

def hash_password(password):
    """Gera o hash de uma senha."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(plain_password, hashed_password):
    """Verifica se a senha fornecida corresponde ao hash."""
    if isinstance(hashed_password, str):
        # Remove 'b'' prefix if present, as it might be stored as a string representation of bytes
        if hashed_password.startswith("b'") and hashed_password.endswith("'"):
            hashed_password = hashed_password[2:-1]
        hashed_password = hashed_password.encode('utf-8')
    elif not isinstance(hashed_password, bytes):
        # Ensure it's bytes if it's not a string or already bytes
        # This part handles cases where it might be a non-string/non-bytes type
        # It converts it to string then encodes, similar to the string case.
        # Adding a check for 'b'' prefix for this scenario too.
        hashed_password_str = str(hashed_password)
        if hashed_password_str.startswith("b'") and hashed_password_str.endswith("'"):
            hashed_password_str = hashed_password_str[2:-1]
        hashed_password = hashed_password_str.encode('utf-8')

    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

def get_status_indicator(prazo, status):
    """Retorna o emoji indicador com base no prazo e status do processo."""
    if status == "Concluído":
        return INDICADORES_STATUS["Concluído"]
    if status == "Cancelado":
        return INDICADORES_STATUS["Cancelado"]

    hoje = datetime.now().date()
    prazo_data = pd.to_datetime(prazo).date() if pd.notna(prazo) else None
    
    if prazo_data is None:
        return ""

    if prazo_data < hoje:
        return INDICADORES_STATUS["Prazo vencido"]
    elif prazo_data <= hoje + timedelta(days=DIAS_ALERTA_PRAZO):
        return INDICADORES_STATUS["Prazo próximo"]
    else:
        return INDICADORES_STATUS["Em dia"]
