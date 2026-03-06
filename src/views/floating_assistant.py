import streamlit as st
import time
from services import assistant_manager
from data import repository_excel as repository

def display_floating_assistant():
    """Exibe o assistente flutuante no canto inferior direito."""
    
    # CSS específico para a bolha do assistente
    st.markdown("""
        <style>
        /* Container específico para o Assistente Flutuante */
        #floating-assistant-root [data-testid="stPopover"] {
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 999999;
        }
        
        /* Botão da Bolha Estilizado */
        #floating-assistant-root [data-testid="stPopover"] > button {
            border-radius: 50% !important;
            width: 70px !important;
            height: 70px !important;
            background-color: #1E3A8A !important;
            color: white !important;
            border: 2px solid #FFFFFF !important;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.4) !important;
            font-size: 32px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.3s ease !important;
        }
        
        #floating-assistant-root [data-testid="stPopover"] > button:hover {
            transform: scale(1.1) !important;
            background-color: #2563EB !important;
            box-shadow: 0px 6px 20px rgba(0,0,0,0.5) !important;
        }

        /* Janela de Chat */
        #floating-assistant-root [data-testid="stPopoverBody"] {
            width: 350px !important;
            max-height: 500px !important;
            border-radius: 15px !important;
            border: 1px solid #E5E7EB !important;
            box-shadow: 0px 10px 25px rgba(0,0,0,0.1) !important;
            padding: 15px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Wrap the popover in a div with the ID we use in CSS
    st.markdown('<div id="floating-assistant-root">', unsafe_allow_html=True)
    with st.popover("🤖"):
        st.subheader("🤖 Assistente Ideal", divider="blue")
        st.caption("Olá! Sou o Jarvis, seu Assistente Ideal. Como posso te ajudar hoje?")

        # Botões de atalho rápido
        c1, c2 = st.columns(2)
        if c1.button("❓ Ajuda", use_container_width=True, key="float_btn_ajuda"):
            st.session_state.last_jarvis_res = assistant_manager.ask_jarvis("ajuda")
            st.rerun()
        if c2.button("📖 Tutoriais", use_container_width=True, key="float_btn_tut"):
            st.session_state.last_jarvis_res = assistant_manager.ask_jarvis("tutorial")
            st.rerun()
        
        st.divider()
        
        if "assistant_reset" not in st.session_state:
            st.session_state.assistant_reset = 0
        
        # Interface de pergunta
        with st.form(key=f"float_form_{st.session_state.assistant_reset}", clear_on_submit=True):
            user_q = st.text_input("Sua dúvida:", placeholder="Ex: alerta amarelo, como cadastrar...")
            submit_button = st.form_submit_button("🚀 Perguntar", use_container_width=True)
            
            if submit_button and user_q:
                st.session_state.last_query = user_q
                st.session_state.last_jarvis_res = assistant_manager.ask_jarvis(user_q)
                st.session_state.assistant_reset += 1
                st.rerun()
        
        # Exibição da resposta
        if "last_jarvis_res" in st.session_state:
            st.info(st.session_state.last_jarvis_res)
            
            # Feedback
            st.caption("A resposta foi útil?")
            fb_col1, fb_col2, fb_col3 = st.columns([1, 1, 1.5])
            
            if fb_col1.button("👍 Sim", key="float_fb_yes"):
                st.toast("Fico feliz em ajudar!", icon="✅")
                del st.session_state.last_jarvis_res
                st.rerun()
            
            if fb_col2.button("👎 Não", key="float_fb_no"):
                st.session_state.show_suggestion_float = True
            
            if fb_col3.button("Limpar", type="secondary", key="float_fb_clear"):
                del st.session_state.last_jarvis_res
                if "show_suggestion_float" in st.session_state: del st.session_state.show_suggestion_float
                st.rerun()

            if st.session_state.get("show_suggestion_float"):
                st.divider()
                st.caption("Como eu deveria ter respondido?")
                suggestion = st.text_area("Sua sugestão:", key="float_sug_text", height=100)
                if st.button("Enviar Sugestão", use_container_width=True, key="float_btn_sug"):
                    if suggestion:
                        user = st.session_state.get('user', {'Nome': 'Usuário'})
                        repository.suggest_knowledge(st.session_state.get("last_query", "geral"), suggestion, user['Nome'])
                        st.success("Obrigado! Sugestão enviada.")
                        time.sleep(1)
                        del st.session_state.last_jarvis_res
                        st.session_state.show_suggestion_float = False
                        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
