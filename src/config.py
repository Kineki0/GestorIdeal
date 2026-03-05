# config.py

# --- Configurações Gerais do CRM ---
DATABASE_PATH = "data_excel/database.xlsx"

# --- Fluxo Operacional Travado ---
ETAPAS_KANBAN = [
    "Leads",
    "Em Progresso",
    "Pendentes",
    "Propostas",
    "Reuniões",
    "Negociação",
    "Ganhos",
    "Perdidos"
]

# --- Configurações de Tags e Classificação ---
TAGS_PRIORIDADE = ["Baixa", "Média", "Alta"]
TAGS_RISCO = ["Baixo", "Médio", "Alto", "Crítico"]
TAGS_ESFORCO = ["Baixo", "Médio", "Alto"]
TAGS_STATUS = ["Em dia", "Aguardando", "Atrasado", "Urgente"]

# --- Núcleos de Serviço ---
NUCLEOS = ["Comercial", "Operacional", "Financeiro", "Jurídico", "Estratégico"]

# --- Configurações de Interface ---
INDICADORES_STATUS = {
    "Prazo vencido": "🔴",
    "Prazo próximo": "🟡",
    "Em dia": "🟢"
}
DIAS_ALERTA_PRAZO = 3
