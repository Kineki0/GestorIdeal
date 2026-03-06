# assistant_manager.py
import re

# Base de Conhecimento do Jarvis (FAQ Pré-programada)
KNOWLEDGE_BASE = {
    "cadastro": "Para cadastrar um novo lead, clique no botão '＋ NOVO LEAD' no topo do Kanban. Lembre-se: Telefone (8-11 dígitos), CNPJ (14 dígitos) e Razão Social são obrigatórios.",
    "cnpj": "O CNPJ deve conter exatamente 14 números. O sistema limpa automaticamente pontos e traços, mas a quantidade de dígitos deve estar correta.",
    "telefone": "O telefone aceita de 8 a 11 dígitos. Você pode digitar com ou sem DDD. O sistema formatará automaticamente para o banco de dados.",
    "alerta": "O ícone ⚠️ (ESTAGNADO) aparece nos cards que estão na mesma etapa há mais de 5 dias. É um sinal para o comercial dar atenção prioritária a esse lead.",
    "aging": "O aging (envelhecimento) mede quantos dias o lead está na fase atual. Se passar de 5 dias, o Jarvis aciona um alerta visual no card.",
    "checklist": "As tarefas do checklist são automáticas! Ao mover um lead para uma nova etapa, as tarefas padrão daquela fase são adicionadas sem apagar as anteriores.",
    "relatorio": "Para gerar um relatório Excel, vá até a página 'Dashboard' e use o botão '📊 GERAR RELATÓRIO EXCEL' na barra lateral esquerda.",
    "backup": "O Jarvis faz backups automáticos diários para a pasta 'Backups' no seu Google Drive. Você não precisa se preocupar com a perda de dados!",
    "drive": "Todos os anexos são salvos no Google Drive em uma estrutura organizada por Ano > Mês > Categoria > ID do Lead.",
    "excluir": "A exclusão de leads e anexos é permitida apenas para usuários com perfil 'Admin'. Usuários comuns não podem deletar registros por segurança.",
    "mover": "Você pode mover um lead abrindo os detalhes do card e usando os botões 'Avançar' ou 'Recuar'. Isso disparará automaticamente o novo checklist da fase.",
    "venda": "Ao concluir uma negociação, use o botão '🏆 GANHO' nos detalhes do lead. Isso moverá o card para a coluna de Ganhos e gerará métricas no Dashboard."
}

def ask_jarvis(query):
    """
    Processa a pergunta do usuário e retorna a melhor resposta da base de conhecimento.
    Usa busca por palavras-chave simples.
    """
    query = query.lower()
    
    # Busca por correspondência de palavras-chave
    for key, response in KNOWLEDGE_BASE.items():
        if key in query:
            return response
            
    return "Desculpe, ainda não tenho essa informação na minha base de conhecimento. Tente perguntar sobre 'cadastro', 'alerta', 'checklist' ou 'relatórios'."
