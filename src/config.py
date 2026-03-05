# config.py

# --- Configurações Gerais do CRM ---
DATABASE_PATH = "data_excel/database.xlsx"

# --- Configurações do Kanban ---
ETAPAS_KANBAN = [
    "Recebido",
    "Em Execução",
    "Aguardando Cliente",
    "Aguardando Interno",
    "Follow-up", # Added Follow-up stage
    "Qualificado", # Added Qualificado stage
    "Concluído",
    "Cancelado"
]

# Lista apenas com as etapas ativas, para uso no selectbox de movimentação
ETAPAS_ATIVAS = [
    "Recebido",
    "Em Execução",
    "Aguardando Cliente",
    "Aguardando Interno",
    "Follow-up",
    "Qualificado"
]

# Novas definições para o Dashboard
ETAPA_FOLLOWUP = "Follow-up"
ETAPAS_QUALIFICADO = ["Qualificado", "Concluído"] # Assuming "Concluído" is also qualified

TAGS_PROCESSO = [
    "Urgente",
    "Financeiro",
    "Jurídico",
    "Marketing",
    "Técnico"
]

# SLA padrão em dias por serviço (exemplo)
SLA_SERVICO = {
    "Desenvolvimento de Website": 30,
    "Consultoria de SEO": 15,
    "Gestão de Redes Sociais": 5
}

# --- Configurações de Usuários ---
PERFIS_USUARIO = {
    "Admin": "Administrador",
    "Operacional": "Operacional",
    "Visualizacao": "Visualização"
}

# --- Configurações de Indicadores e Alertas ---
INDICADORES_STATUS = {
    "Prazo vencido": "⏰",
    "Prazo próximo": "⚠️",
    "Concluído": "✅",
    "Cancelado": "❌",
    "Em dia": "👍" 
}
DIAS_ALERTA_PRAZO = 3

# --- Configurações de Integração (Google Drive) ---
# O ID da pasta raiz e as credenciais da conta de serviço
# devem ser configurados no arquivo .streamlit/secrets.toml
# e NÃO aqui diretamente.