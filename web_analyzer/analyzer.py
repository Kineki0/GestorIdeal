# analyzer.py
import config

def analyze_results(search_results, target_company, base_contratos_nomes):
    """
    Analisa os resultados da busca para classificar a relação com a empresa.

    :param search_results: Lista de resultados da busca do web_searcher.
    :param target_company: Nome da empresa-alvo.
    :param base_contratos_nomes: Uma lista (ou set) com nomes de empresas que já têm contrato.
    :return: Uma tupla (classificação, evidência, fonte, link, grau_confianca).
    """
    # Se a empresa já está na base de contratos, a confiança é alta por padrão.
    if target_company.lower() in (name.lower() for name in base_contratos_nomes):
        status_base = "Contrato Confirmado (Base Interna)"
        confianca_base = 100
    else:
        status_base = None
        confianca_base = 0
        
    if not search_results:
        if status_base:
            return "Contrato Confirmado", "Confirmado via base interna, sem evidência pública encontrada.", "Base Interna", "", 100
        return "Sem Evidência de Contrato", "Nenhuma menção pública encontrada.", "", "", 0

    melhor_evidencia = None
    maior_pontuacao = 0

    for res in search_results:
        snippet = res['snippet'].lower()
        title = res['title'].lower()
        texto_completo = f"{title} {snippet}"
        pontuacao_atual = 0

        # Verifica a presença de termos de relação
        termos_encontrados = [termo for termo in config.TERMOS_DE_RELACAO if termo in texto_completo]
        
        if termos_encontrados:
            # A pontuação pode ser mais sofisticada, aqui é um exemplo simples
            pontuacao_atual += config.PONTUACAO_EVIDENCIA.get("Mencao_Explicita_Site_Oficial", 50)
            
            evidencia_atual = {
                "texto": f"Termos encontrados: {', '.join(termos_encontrados)}. Trecho: '{res['snippet']}'",
                "fonte": res.get('link').split('/')[2], # Extrai o domínio principal
                "link": res.get('link'),
                "pontuacao": pontuacao_atual
            }
            
            if pontuacao_atual > maior_pontuacao:
                maior_pontuacao = pontuacao_atual
                melhor_evidencia = evidencia_atual

    # Combina a confiança da base interna com a evidência pública
    grau_confianca_final = max(maior_pontuacao, confianca_base)

    if grau_confianca_final >= 100:
        classificacao = "Contrato Confirmado"
    elif grau_confianca_final >= config.LIMIAR_CONFIANCA_POSSIVEL:
        classificacao = "Possível Relação (verificar)"
    else:
        if status_base: # Se estava na base, mas sem evidência pública forte
            return "Contrato Confirmado", "Confirmado via base interna, sem nova evidência pública.", "Base Interna", "", 100
        return "Sem Evidência de Contrato", "Menções encontradas não são conclusivas.", "", "", grau_confianca_final

    return (
        classificacao,
        melhor_evidencia['texto'],
        melhor_evidencia['fonte'],
        melhor_evidencia['link'],
        grau_confianca_final
    )
