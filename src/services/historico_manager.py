# historico_manager.py
import streamlit as st
import pandas as pd
from data import repository_excel as repository

def display_history_for_lead(lead_id):
    """
    Busca e exibe o histórico para um lead específico em um formato legível.
    """
    st.write("#### Histórico de Alterações")
    
    historico_df = repository.get_all('Historico')

    if historico_df.empty:
        st.info("Nenhum registro de histórico encontrado no sistema.")
        return

    lead_history = historico_df[historico_df['ID_Lead'] == lead_id].copy()

    if lead_history.empty:
        st.info("Este lead ainda não possui registros de histórico.")
        return
        
    lead_history.sort_values(by='Timestamp', ascending=False, inplace=True)
    
    # --- Filtros ---
    col1, col2 = st.columns(2)
    usuarios = ["Todos"] + lead_history['Usuario'].unique().tolist()
    usuario_filtro = col1.selectbox("Filtrar por usuário", options=usuarios, key=f"hist_user_{lead_id}")
    data_filtro = col2.date_input("Filtrar por data", value=None, key=f"hist_date_{lead_id}")

    if usuario_filtro != "Todos":
        lead_history = lead_history[lead_history['Usuario'] == usuario_filtro]
    if data_filtro:
        lead_history = lead_history[lead_history['Timestamp'].dt.date == data_filtro]

    # --- Exibição ---
    if lead_history.empty:
        st.warning("Nenhum registro encontrado para os filtros aplicados.")
    else:
        for _, row in lead_history.iterrows():
            with st.expander(f"📅 {row['Timestamp'].strftime('%d/%m/%Y %H:%M')} por {row['Usuario']}"):
                st.markdown(
                    f"""
                    O campo **`{row['Campo_Alterado']}`** mudou de 
                    <span style="background-color:#ffeeba; padding:2px 4px; border-radius:3px; font-family:monospace;">{row['Valor_Antigo']}</span> 
                    para 
                    <span style="background-color:#d4edda; padding:2px 4px; border-radius:3px; font-family:monospace;">{row['Valor_Novo']}</span>.
                    """,
                    unsafe_allow_html=True
                )
                if pd.notna(row['Comentario']) and row['Comentario']:
                    st.info(f"**Comentário:** {row['Comentario']}")
