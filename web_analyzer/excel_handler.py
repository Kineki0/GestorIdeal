# excel_handler.py
import pandas as pd
from datetime import datetime
import config
import os

def load_input_files():
    """
    Carrega os arquivos Excel de entrada.
    - base_contratos.xlsx
    - empresas_a_pesquisar.xlsx

    :return: Uma tupla de DataFrames (df_base_contratos, df_empresas_a_pesquisar).
    """
    try:
        df_base_contratos = pd.read_excel(config.ARQUIVO_BASE_CONTRATOS)
        print(f"Arquivo '{config.ARQUIVO_BASE_CONTRATOS}' carregado com sucesso.")
    except FileNotFoundError:
        print(f"AVISO: Arquivo '{config.ARQUIVO_BASE_CONTRATOS}' não encontrado. A verificação continuará sem uma base de referência.")
        df_base_contratos = pd.DataFrame(columns=['Nome_Empresa', 'CNPJ', 'Status_Contrato'])

    try:
        df_empresas_a_pesquisar = pd.read_excel(config.ARQUIVO_EMPRESAS_A_PESQUISAR)
        print(f"Arquivo '{config.ARQUIVO_EMPRESAS_A_PESQUISAR}' carregado com sucesso. {len(df_empresas_a_pesquisar)} empresas para analisar.")
    except FileNotFoundError:
        print(f"ERRO: Arquivo de entrada '{config.ARQUIVO_EMPRESAS_A_PESQUISAR}' não encontrado. O programa não pode continuar.")
        return None, None
        
    return df_base_contratos, df_empresas_a_pesquisar

def save_report(results):
    """
    Salva os resultados da análise em um novo arquivo Excel com múltiplas abas.

    :param results: Um dicionário contendo DataFrames para cada aba do relatório.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = config.OUTPUT_FILENAME_TEMPLATE.format(timestamp=timestamp)
    
    try:
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for sheet_name, df in results.items():
                if not df.empty:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        print(f"\nRelatório salvo com sucesso como '{filename}'")
        # Abre o arquivo automaticamente no final (opcional, pode ser específico do OS)
        # import subprocess
        # subprocess.run(['start', filename], shell=True) # Para Windows

    except Exception as e:
        print(f"ERRO: Não foi possível salvar o relatório em Excel. Erro: {e}")

def initialize_results_dataframes():
    """
    Cria um dicionário de DataFrames vazios para armazenar os resultados.
    """
    results = {
        "Empresas_Com_Contrato": pd.DataFrame(columns=[
            'Nome_Empresa', 'CNPJ', 'Evidencia_Contrato', 'Fonte', 'Link', 'Data_Verificacao'
        ]),
        "Empresas_Sem_Contrato": pd.DataFrame(columns=[
            'Nome_Empresa', 'CNPJ', 'Observacao', 'Data_Verificacao'
        ]),
        "Possiveis_Contratos": pd.DataFrame(columns=[
            'Nome_Empresa', 'CNPJ', 'Grau_Confianca', 'Evidencia', 'Fonte', 'Link', 'Data_Verificacao'
        ]),
        "Log_Pesquisa": pd.DataFrame(columns=[
            'Nome_Empresa', 'Termos_Utilizados', 'Status_Resultado', 'Erros'
        ])
    }
    return results
