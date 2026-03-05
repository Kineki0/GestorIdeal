# email_manager.py
import base64
import streamlit as st
import os
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from services import drive_manager

def send_email(to, subject, body, is_html=True):
    """
    Envia um e-mail usando a Gmail API via OAuth 2.0.
    Lê as credenciais diretamente do token.json para garantir escopos atualizados.
    """
    try:
        from google.oauth2.credentials import Credentials
        if not os.path.exists('token.json'):
            st.error("Token de autenticação não encontrado. Por favor, conecte ao Google Drive primeiro.")
            return None

        creds = Credentials.from_authorized_user_file('token.json', drive_manager.SCOPES)
        service = build('gmail', 'v1', credentials=creds)

        # Cria a mensagem com suporte a HTML
        message = MIMEText(body, 'html' if is_html else 'plain')
        message['to'] = to
        message['subject'] = subject

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        send_result = service.users().messages().send(
            userId="me", 
            body={'raw': raw_message}
        ).execute()
        
        return send_result
    except Exception as e:
        st.error(f"Erro ao enviar e-mail para {to}: {e}")
        return None

def send_password_reset_email(email, token):
    """
    Envia o e-mail específico de recuperação de senha com layout profissional em HTML.
    """
    subject = "🔑 Recuperação de Senha - Ideal CRM"
    
    # Template HTML Profissional
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
            <div style="background-color: #007bff; color: #ffffff; padding: 20px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">Ideal CRM</h1>
            </div>
            <div style="padding: 30px; color: #333333;">
                <p style="font-size: 16px;">Olá,</p>
                <p style="font-size: 16px;">Recebemos uma solicitação para redefinir a senha da sua conta no <strong>Ideal CRM</strong>.</p>
                <p style="font-size: 16px;">Para prosseguir, utilize o código de verificação abaixo no sistema:</p>
                
                <div style="background-color: #f8f9fa; border: 1px dashed #007bff; padding: 20px; text-align: center; margin: 30px 0; border-radius: 4px;">
                    <span style="font-size: 32px; font-weight: bold; color: #007bff; letter-spacing: 5px;">{token}</span>
                </div>
                
                <p style="font-size: 14px; color: #666666;">Este código é válido por 1 hora. Se você não solicitou esta alteração, nenhuma ação é necessária e você pode ignorar este e-mail com segurança.</p>
            </div>
            <div style="background-color: #f8f9fa; color: #999999; padding: 15px; text-align: center; font-size: 12px;">
                <p style="margin: 0;">&copy; 2026 Equipe Ideal CRM. Todos os direitos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(email, subject, html_content, is_html=True)
