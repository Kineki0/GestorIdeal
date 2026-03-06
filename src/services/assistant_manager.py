# assistant_manager.py

from data import repository_excel as repository

# Base de Conhecimento Fixa (Tutoriais e Sistema)
STATIC_KNOWLEDGE = {
    "ajuda": """
    🌟 **Eu posso te ajudar com os seguintes temas:**
    - **cadastro**: Como criar novos leads corretamente.
    - **fluxo**: Entenda as etapas do Kanban.
    - **aging**: O que significa o alerta de atraso ⚠️.
    - **checklist**: Como as tarefas automáticas funcionam.
    - **anexos**: Como enviar e gerenciar arquivos.
    - **relatorio**: Como exportar dados para o Excel.
    - **backup**: Segurança dos seus dados.
    - **tutorial**: Lista de guias passo a passo disponíveis.
    
    *Digite o nome do tema ou uma pergunta sobre ele!*
    """,
    
    "tutorial": """
    📖 **Tutoriais Disponíveis:**
    1. **Tutorial Cadastro**: Passo a passo do registro inicial.
    2. **Tutorial Movimentação**: Como avançar um lead no funil.
    3. **Tutorial Arquivos**: Como subir e deletar documentos no Drive.
    4. **Tutorial Dashboard**: Como ler os gráficos de performance.
    
    *Diga: 'quero o tutorial de cadastro' para começar.*
    """,

    "tutorial cadastro": """
    🚀 **PASSO A PASSO: CADASTRO DE LEAD**
    1. Clique no botão azul **'＋ NOVO LEAD'** no topo do Kanban.
    2. Insira a **Razão Social** (Nome da Empresa).
    3. Digite o **Telefone** (O sistema aceita de 8 a 11 dígitos).
    4. Digite o **CNPJ** (Apenas os 14 números, sem pontos).
    5. Clique em **'CADASTRAR'**.
    ✅ O lead aparecerá na primeira coluna e o Jarvis criará o primeiro checklist automaticamente!
    """,

    "tutorial movimentação": """
    🔄 **COMO MOVER UM LEAD NO FUNIL**
    1. Localize o card no Kanban e **clique nele**.
    2. No topo da janela que abriu, você verá os botões **'⬅️ Recuar'** ou **'➡️ Avançar'**.
    3. Ao clicar em Avançar, o Jarvis:
       - Move o card para a próxima coluna.
       - Registra a data da mudança no histórico.
       - **Adiciona novas tarefas** ao checklist daquela etapa.
    4. Se a venda fechar, use o botão **'🏆 GANHO'**.
    """,

    "tutorial arquivos": """
    📂 **GESTÃO DE DOCUMENTOS NO DRIVE**
    1. Abra o card do lead e vá na aba **'📂 Arquivos'**.
    2. Clique em **'Browse files'** e escolha seu arquivo (PDF, Imagem, Excel, etc).
    3. O Jarvis enviará para a pasta correta no Google Drive automaticamente.
    4. Para abrir, clique no botão azul **'🔗 ABRIR'**.
    5. Se enviou errado, clique no botão **'🗑️ EXCLUIR'** para remover do banco de dados.
    """,
}

def ask_jarvis(query):
    query = query.lower().strip()
    
    # 1. Busca no Banco de Dados Dinâmico (Excel - Aprovado)
    dynamic_kb = repository.get_active_knowledge()
    for key, response in dynamic_kb.items():
        if key in query:
            return response
    
    # 2. Busca na Base Fixa (Tutoriais)
    if "ajuda" in query or "help" in query or "socorro" in query:
        return STATIC_KNOWLEDGE["ajuda"]
    
    if "tutorial" in query:
        for key in STATIC_KNOWLEDGE:
            if key in query and key != "tutorial":
                return STATIC_KNOWLEDGE[key]
        return STATIC_KNOWLEDGE["tutorial"]

    for key, response in STATIC_KNOWLEDGE.items():
        if key in query:
            return response
            
    return "Hm, ainda estou aprendendo sobre isso. Tente digitar **'ajuda'** ou pergunte de outra forma!"
