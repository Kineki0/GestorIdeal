# web_searcher.py
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import config

def search_google(query, num_results=5):
    """
    Realiza uma busca na web usando a Google Custom Search JSON API.

    :param query: A string de busca.
    :param num_results: O número de resultados a serem retornados (máx. 10).
    :return: Uma lista de dicionários com os resultados ou None em caso de erro.
    """
    if config.GOOGLE_API_KEY == "SUA_API_KEY_AQUI" or config.GOOGLE_CSE_ID == "SEU_CSE_ID_AQUI":
        print("ERRO: As credenciais da API do Google (GOOGLE_API_KEY e GOOGLE_CSE_ID) não foram configuradas em config.py.")
        print("A pesquisa web será pulada. Por favor, configure as credenciais.")
        return None

    try:
        service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
        
        # Rate limiting simples para não exceder quotas rapidamente
        time.sleep(1) 
        
        result = service.cse().list(
            q=query,
            cx=config.GOOGLE_CSE_ID,
            num=num_results
        ).execute()

        if 'items' not in result:
            return []

        # Formata os resultados para um formato mais simples
        formatted_results = []
        for item in result.get('items', []):
            formatted_results.append({
                'title': item.get('title'),
                'link': item.get('link'),
                'snippet': item.get('snippet')
            })
        return formatted_results

    except HttpError as e:
        # Trata erros comuns da API, como quota excedida ou chave inválida
        print(f"ERRO HTTP ao buscar por '{query}': {e}")
        if e.resp.status == 403:
            print("Causa provável: Quota diária gratuita da API excedida.")
        elif e.resp.status == 400:
            print("Causa provável: Chave de API ou CSE ID inválido.")
        return None
    except Exception as e:
        print(f"Um erro inesperado ocorreu durante a busca por '{query}': {e}")
        return None

def build_queries(target_company, site_oficial=None):
    """
    Constrói uma lista de queries de busca inteligentes para uma empresa.
    """
    queries = []
    minha_empresa = f'"{config.MINHA_EMPRESA_NOME}"'
    target_company_quoted = f'"{target_company}"'

    # 1. Queries de alta precisão (no site oficial, se fornecido)
    if site_oficial:
        for termo in config.TERMOS_DE_RELACAO:
            queries.append(f'{minha_empresa} {termo} site:{site_oficial}')

    # 2. Queries gerais
    for termo in config.TERMOS_DE_RELACAO:
        queries.append(f'{target_company_quoted} {minha_empresa} {termo}')

    # 3. Query genérica de associação
    queries.append(f'{target_company_quoted} {minha_empresa}')
    
    return list(set(queries)) # Remove duplicatas
