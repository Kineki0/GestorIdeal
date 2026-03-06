# research_manager.py
import streamlit as st
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def research_company(company_name):
    """
    Pesquisa informações básicas sobre a empresa no Google.
    Retorna site, linkedin e um resumo (snippet).
    """
    api_key = st.secrets.get("GOOGLE_API_KEY")
    cse_id = st.secrets.get("GOOGLE_CSE_ID")
    
    if not api_key or not cse_id:
        return {"error": "API do Google não configurada nos Secrets."}

    try:
        service = build("customsearch", "v1", developerKey=api_key)
        
        # Query principal
        query = f'"{company_name}" site linkedin oficial'
        
        result = service.cse().list(
            q=query,
            cx=cse_id,
            num=5
        ).execute()

        items = result.get('items', [])
        if not items:
            return {"error": "Nenhum dado encontrado para esta empresa."}

        # Extração inteligente
        data = {
            "site": "",
            "linkedin": "",
            "description": ""
        }
        
        descriptions = []
        for item in items:
            link = item.get('link', '')
            snippet = item.get('snippet', '')
            
            if "linkedin.com/company" in link and not data["linkedin"]:
                data["linkedin"] = link
            elif not data["site"] and "facebook" not in link and "instagram" not in link:
                data["site"] = link
            
            descriptions.append(snippet)

        # Junta os primeiros snippets para formar uma descrição
        data["description"] = " | ".join(descriptions[:2])
        
        return data

    except HttpError as e:
        return {"error": f"Erro na API: {e}"}
    except Exception as e:
        return {"error": str(e)}
