# assistant_manager.py
from data import repository_excel as repository

# Base de Conhecimento Fixa (Respostas + Tutoriais Integrados)
STATIC_KNOWLEDGE = {
    "cadastro": """
    📝 **SOBRE CADASTRO DE LEADS:**
    Para cadastrar um novo lead, use o botão azul **'＋ NOVO LEAD'**. Razão Social, Telefone, Contato e CNPJ são obrigatórios.
    
    🚀 **PASSO A PASSO (TUTORIAL):**
    1. Clique em **'＋ NOVO LEAD'** no topo do Kanban.
    2. Insira os dados (Telefone: 8-11 dígitos | CNPJ: 14 dígitos).
    3. Clique em **'CADASTRAR'**.
    ✅ O lead aparecerá na primeira coluna com o checklist inicial!
    """,

    "fluxo": """
    🔄 **SOBRE O FLUXO (MOVIMENTAÇÃO):**
    O lead entra em 'Leads' e deve avançar até 'Ganhos'. Mover o lead atualiza o histórico e as tarefas.
    
    🚀 **PASSO A PASSO (TUTORIAL):**
    1. Clique no card do lead.
    2. Use os botões **'⬅️ Recuar'** ou **'➡️ Avançar'** no topo.
    3. Ao avançar, o Jarvis adiciona as novas tarefas daquela fase automaticamente!
    """,

    "aging": """
    ⚠️ **O QUE É AGING (ENVELHECIMENTO)?**
    O aging mede o tempo que um lead está parado em uma etapa. Se ele ficar mais de 5 dias sem movimentação, o Jarvis ativa o **Alerta Amarelo** no card.
    """,

    "alerta amarelo": """
    ⚠️ **POR QUE O ALERTA AMARELO?**
    O alerta ⚠️ (ESTAGNADO) aparece automaticamente quando um lead está na mesma etapa do Kanban há mais de **5 dias**.
    
    💡 **Dica do Jarvis:** Isso serve para sinalizar que o lead precisa de atenção imediata ou um novo follow-up para não esfriar a venda.
    """,

    "checklist": """
    ✅ **SOBRE CHECKLISTS AUTOMÁTICOS:**
    Cada etapa do processo tem tarefas padrão. O Jarvis insere essas tarefas assim que o lead chega na fase.
    
    💡 **Como usar:** Marque as tarefas como concluídas na aba 'Checklist' para ver o gráfico de progresso subir!
    """,

    "anexos": """
    📂 **SOBRE ARQUIVOS E DOCUMENTOS:**
    Todos os arquivos são salvos de forma organizada no seu Google Drive.
    
    🚀 **PASSO A PASSO (TUTORIAL):**
    1. Abra o card do lead e vá na aba **'📂 Arquivos'**.
    2. Selecione o arquivo no botão de upload.
    3. Para visualizar, clique em **'🔗 ABRIR'**.
    """,

    "arquivos": """
    📂 **SOBRE ARQUIVOS E DOCUMENTOS:**
    Todos os arquivos são salvos de forma organizada no seu Google Drive.
    
    🚀 **PASSO A PASSO (TUTORIAL):**
    1. Abra o card do lead e vá na aba **'📂 Arquivos'**.
    2. Selecione o arquivo no botão de upload.
    3. Para visualizar, clique em **'🔗 ABRIR'**.
    """,

    "relatorio": """
    📊 **RELATÓRIOS EXCEL:**
    Para extrair dados, vá ao 'Dashboard' e clique em **'📊 GERAR RELATÓRIO EXCEL'** na sidebar. 
    O Jarvis criará um arquivo completo com Leads, Resumo de Etapas e Histórico.
    """,

    "backup": "O Jarvis salva uma cópia completa do seu banco de dados todos os dias na pasta 'Backups' do Google Drive. Seus dados estão 100% protegidos.",

    "tutorial": """
    📖 **TUTORIAIS DISPONÍVEIS:**
    - Digite **'tutorial cadastro'** para ver como registrar leads.
    - Digite **'tutorial movimentação'** para ver como usar o funil.
    - Digite **'tutorial arquivos'** para aprender sobre o Drive.
    """,
    
    "ajuda": """
    🌟 **EU POSSO TE AJUDAR COM:**
    - **cadastro**: Como criar leads.
    - **fluxo**: Como mover os cards.
    - **alerta amarelo**: O que é o aviso ⚠️.
    - **checklist**: Tarefas automáticas.
    - **arquivos**: Como anexar documentos.
    - **relatorio**: Como baixar o Excel.
    - **backup**: Segurança dos dados.
    """
}

def ask_jarvis(query):
    # Limpeza profunda da pergunta
    query = query.lower().replace(":", "").replace("?", "").strip()
    
    # 1. Busca no Banco de Dados Dinâmico (Excel - Aprovado)
    try:
        dynamic_kb = repository.get_active_knowledge()
        for key, response in dynamic_kb.items():
            if key in query:
                return response
    except: pass
    
    # 2. Busca na Base Fixa (Prioridade para termos exatos)
    # Se o usuário digitar exatamente uma das chaves
    if query in STATIC_KNOWLEDGE:
        return STATIC_KNOWLEDGE[query]

    # 3. Busca por correspondência parcial (se a palavra-chave estiver dentro da frase)
    # Ordenamos pelas chaves mais longas primeiro para evitar que 'alerta' pegue o lugar de 'alerta amarelo'
    sorted_keys = sorted(STATIC_KNOWLEDGE.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if key in query:
            return STATIC_KNOWLEDGE[key]
    
    # 4. Comandos de socorro
    if "ajuda" in query or "help" in query or "socorro" in query:
        return STATIC_KNOWLEDGE["ajuda"]
            
    return "Hm, ainda estou aprendendo sobre isso. Tente digitar apenas uma palavra como **'cadastro'**, **'alerta'** ou **'relatorio'**."
