# CRM Pro Kanban com Anexos no Google Drive

Este é um sistema de CRM visual e multiusuário, construído com Python e Streamlit, que agora suporta a gestão de anexos diretamente no Google Drive. Ele mantém a base de dados de metadados em Excel, oferecendo uma solução completa e integrada para gestão de processos e documentos.

## ✨ Funcionalidades Principais

- **Gestão de Anexos em Nuvem:** Faça upload, liste e acesse arquivos de processos, clientes e serviços, armazenados de forma segura e organizada no Google Drive.
- **Sistema Multiusuário Local:** Autenticação segura com perfis de acesso (`Admin`, `Operacional`, `Visualização`).
- **Auditoria Completa:** Rastreabilidade de todas as ações, incluindo o upload de anexos, com registro de usuário e data.
- **Comentários no Histórico:** Adicione comentários a qualquer processo, registrando observações e comunicações importantes diretamente no histórico do processo.
- **Visões Gerenciais:** Dashboard de métricas, visão de calendário e um quadro Kanban interativo.
- **Arquitetura Desacoplada:** O acesso ao Excel e ao Google Drive é feito através de camadas de serviço (`repository` e `manager`), facilitando a manutenção e futuras evoluções.

---

## ⚙️ **CONFIGURAÇÃO OBRIGATÓRIA: GOOGLE DRIVE**

Para que a funcionalidade de anexos funcione, você **precisa** configurar o acesso ao Google Drive via uma Conta de Serviço.

**Siga estes 4 passos:**

### Passo 1: Criar uma Conta de Serviço e Chave JSON
1. Vá para o [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um novo projeto ou selecione um existente.
3. No menu, vá para **IAM e admin > Contas de serviço**.
4. Clique em **CRIAR CONTA DE SERVIÇO**, dê um nome (ex: `crm-drive-bot`) e clique em "Criar e continuar".
5. No passo de "Conceder a esta conta de serviço acesso ao projeto", não é necessário adicionar papéis. Clique em "Continuar" e depois em "Concluído".
6. Encontre a conta recém-criada na lista, clique nos três pontos em "Ações" e selecione **Gerenciar chaves**.
7. Clique em **ADICIONAR CHAVE > Criar nova chave**. Escolha **JSON** e clique em **CRIAR**. Um arquivo `.json` será baixado. **Guarde-o em um local seguro.**
8. No menu do Google Cloud, vá para **APIs e Serviços > Biblioteca**, procure por **"Google Drive API"** e **ative-a** para o seu projeto.

### Passo 2: Criar e Compartilhar a Pasta no Google Drive
1. Em sua conta do Google Drive, crie uma nova pasta. O nome pode ser, por exemplo, **`CRM_Arquivos`**.
2. Clique com o botão direito na pasta, vá em **Compartilhar > Compartilhar**.
3. No campo "Adicionar pessoas e grupos", cole o **email da Conta de Serviço** que você criou (ex: `crm-drive-bot@meu-projeto.iam.gserviceaccount.com`).
4. Garanta que a permissão seja de **Editor** e clique em "Enviar".

### Passo 3: Configurar o Arquivo `secrets.toml`
1. No diretório do projeto, navegue até a pasta `.streamlit` e abra o arquivo `secrets.toml`.
2. Copie e cole todo o conteúdo do arquivo `.json` que você baixou do Google Cloud para dentro da seção `[gcp_service_account]` do `secrets.toml`.
3. Na pasta do Google Drive que você criou, copie o ID da pasta da URL.
   - Ex: `https://drive.google.com/drive/folders/ID_DA_PASTA_VEM_AQUI`
4. Cole esse ID no campo `DRIVE_ROOT_FOLDER_ID`.

Seu `secrets.toml` deve ficar parecido com isto:
```toml
# .streamlit/secrets.toml
DRIVE_ROOT_FOLDER_ID = "ID_DA_PASTA_VEM_AQUI"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "crm-drive-bot@meu-projeto.iam.gserviceaccount.com"
# ... resto do conteúdo do JSON
```

### Passo 4: Instalar Dependências e Executar
1. Instale/atualize as dependências, que agora incluem as bibliotecas do Google:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute a aplicação:
   ```bash
   streamlit run app.py
   ```

O sistema agora está pronto para usar a funcionalidade de upload e gerenciamento de anexos.