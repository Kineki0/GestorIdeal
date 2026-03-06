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

# --- Automação de Checklist por Etapa ---
CHECKLIST_PADRAO = {
    "Leads": ["Coletar informações básicas", "Validar telefone e email", "Identificar tomador de decisão"],
    "Em Progresso": ["Agendar primeira chamada", "Enviar apresentação da empresa", "Mapear dores do cliente"],
    "Pendentes": ["Solicitar documentos", "Verificar pendências financeiras", "Analisar histórico de crédito"],
    "Propostas": ["Elaborar orçamento", "Revisão técnica da proposta", "Enviar proposta por email"],
    "Reuniões": ["Confirmar presença", "Preparar material de apresentação", "Definir ata de reunião"],
    "Negociação": ["Ajustar valores", "Validar condições de pagamento", "Aprovação final com diretoria"],
    "Ganhos": ["Enviar boas-vindas", "Assinatura do contrato", "Kick-off operacional"],
    "Perdidos": ["Registrar motivo da perda", "Agendar follow-up futuro"]
}
