# assistant_manager.py
from data import repository_excel as repository

# Base de Conhecimento Fixa (Respostas + Tutoriais Integrados)
STATIC_KNOWLEDGE = {
    "ajuda": """
    🌟 **Eu posso te ajudar com os seguintes temas:**
    - **cadastro**: Como criar novos leads corretamente.
    - **fluxo**: Entenda as etapas do Kanban.
    - **aging / alerta amarelo**: O que significa o aviso de atraso ⚠️.
    - **checklist**: Como as tarefas automáticas funcionam.
    - **anexos / arquivos**: Como enviar e gerenciar documentos.
    - **relatorio**: Como exportar dados para o Excel.
    - **backup**: Segurança e snapshots dos seus dados.
    - **tutorial**: Lista de guias passo a passo disponíveis.
    
    *Digite o nome do tema ou uma pergunta sobre ele!*
    """,
    
    "tutorial": """
    📖 **Tutoriais Disponíveis:**
    1. **Tutorial Cadastro**: Passo a passo do registro inicial.
    2. **Tutorial Movimentação**: Como avançar um lead no funil.
    3. **Tutorial Arquivos**: Como subir e deletar documentos no Drive.
    4. **Tutorial Dashboard**: Como ler os gráficos de performance.
    """,

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

    "dashboard": """
    📊 **SOBRE O DASHBOARD:**
    O Dashboard mostra o desempenho do seu time e o volume do funil em tempo real.
    
    🚀 **COMO LER (TUTORIAL):**
    1. **KPIs**: Resumo de vendas e novos leads no topo.
    2. **Funil**: Onde os leads estão acumulados.
    3. **SLA**: Tempo médio que o lead fica em cada etapa.
    """,

    "alerta amarelo": """
    ⚠️ **POR QUE O ALERTA AMARELO?**
    O alerta ⚠️ (ESTAGNADO) aparece automaticamente quando um lead está na mesma etapa do Kanban há mais de **5 dias**.
    
    💡 **Dica do Jarvis:** Isso serve para sinalizar que o lead precisa de atenção imediata ou um novo follow-up para não esfriar a venda.
    """,

    "aging": "O aging mede o tempo de permanência de um lead em uma fase. Se ultrapassar 5 dias, o Jarvis exibe o alerta ⚠️ amarelo no card.",

    "checklist": """
    ✅ **SOBRE CHECKLISTS AUTOMÁTICOS:**
    Cada etapa do processo tem tarefas padrão. O Jarvis insere essas tarefas assim que o lead chega na fase.
    
    💡 **Como usar:** Marque as tarefas como concluídas na aba 'Checklist' para ver o gráfico de progresso subir!
    """,

    "relatorio": "Vá ao 'Dashboard' e clique em **'📊 GERAR RELATÓRIO EXCEL'** na sidebar para baixar todos os dados de leads e histórico.",

    "backup": "O Jarvis salva uma cópia completa do seu banco de dados todos os dias na pasta 'Backups' do Google Drive. Seus dados estão 100% protegidos.",
}

def ask_jarvis(query):
    query = query.lower().strip()
    
    # 1. Busca no Banco de Dados Dinâmico (Excel - Aprovado)
    dynamic_kb = repository.get_active_knowledge()
    for key, response in dynamic_kb.items():
        if key in query:
            return response
    
    # 2. Busca na Base Fixa (Respostas + Tutoriais Integrados)
    if "ajuda" in query or "help" in query or "socorro" in query:
        return STATIC_KNOWLEDGE["ajuda"]
    
    # Busca por correspondência parcial nas palavras-chave
    for key, response in STATIC_KNOWLEDGE.items():
        if key in query:
            return response
            
    return "Hm, ainda estou aprendendo sobre isso. Tente digitar **'ajuda'** para ver meus comandos, ou pergunte sobre **'cadastro'**, **'alerta'** ou **'relatório'**."
