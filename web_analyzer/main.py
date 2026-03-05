# main.py
from datetime import datetime
import pandas as pd
import excel_handler
import web_searcher
import analyzer

def main():
    """
    Função principal que orquestra o processo de pesquisa e análise.
    """
    print("--- Iniciando Automação de Pesquisa Web ---")
    
    # 1. Carregar dados de entrada
    df_base_contratos, df_empresas = excel_handler.load_input_files()
    if df_empresas is None:
        return # Encerra se o arquivo principal não for encontrado

    base_contratos_nomes = set(df_base_contratos['Nome_Empresa'].str.lower())
    
    # 2. Inicializar DataFrames de resultados
    results = excel_handler.initialize_results_dataframes()

    # 3. Iterar sobre cada empresa a ser pesquisada
    for index, row in df_empresas.iterrows():
        empresa_nome = row['Nome_Empresa']
        empresa_cnpj = row.get('CNPJ', '')
        site_oficial = row.get('Site_Oficial', None)
        
        print(f"\n[{index + 1}/{len(df_empresas)}] Analisando: {empresa_nome}")

        # 4. Construir e executar as buscas
        queries = web_searcher.build_queries(empresa_nome, site_oficial)
        all_search_results = []
        log_queries = []

        for query in queries:
            print(f"  -> Executando busca: '{query[:80]}...'")
            search_results = web_searcher.search_google(query)
            log_queries.append(query)
            
            if search_results:
                all_search_results.extend(search_results)
            
            if search_results is None and web_searcher.config.GOOGLE_API_KEY == "SUA_API_KEY_AQUI":
                break # Interrompe se a API não estiver configurada

        # 5. Analisar os resultados compilados
        (classificacao, evidencia, fonte, link, confianca) = analyzer.analyze_results(
            all_search_results, empresa_nome, base_contratos_nomes
        )
        print(f"  ==> Classificação: {classificacao} (Confiança: {confianca}%)")

        # 6. Registrar resultados nos DataFrames corretos
        data_hoje = datetime.now().date()
        
        new_row_log = pd.DataFrame([{'Nome_Empresa': empresa_nome, 'Termos_Utilizados': " | ".join(log_queries), 'Status_Resultado': classificacao, 'Erros': ''}])
        results["Log_Pesquisa"] = pd.concat([results["Log_Pesquisa"], new_row_log], ignore_index=True)

        if classificacao == "Contrato Confirmado":
            new_row = pd.DataFrame([{'Nome_Empresa': empresa_nome, 'CNPJ': empresa_cnpj, 'Evidencia_Contrato': evidencia, 'Fonte': fonte, 'Link': link, 'Data_Verificacao': data_hoje}])
            results["Empresas_Com_Contrato"] = pd.concat([results["Empresas_Com_Contrato"], new_row], ignore_index=True)

        elif classificacao == "Sem Evidência de Contrato":
            new_row = pd.DataFrame([{'Nome_Empresa': empresa_nome, 'CNPJ': empresa_cnpj, 'Observacao': evidencia, 'Data_Verificacao': data_hoje}])
            results["Empresas_Sem_Contrato"] = pd.concat([results["Empresas_Sem_Contrato"], new_row], ignore_index=True)
            
        elif classificacao == "Possível Relação (verificar)":
            new_row = pd.DataFrame([{'Nome_Empresa': empresa_nome, 'CNPJ': empresa_cnpj, 'Grau_Confianca': confianca, 'Evidencia': evidencia, 'Fonte': fonte, 'Link': link, 'Data_Verificacao': data_hoje}])
            results["Possiveis_Contratos"] = pd.concat([results["Possiveis_Contratos"], new_row], ignore_index=True)

    # 7. Salvar o relatório final
    excel_handler.save_report(results)
    
    print("\n--- Automação de Pesquisa Web Concluída ---")

if __name__ == "__main__":
    main()
