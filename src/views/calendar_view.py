# calendar_view.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from data import repository_excel as repository
import utils

def display():
    """
    Exibe uma visão de calendário/agenda dos leads, agrupados por data de prazo.
    """
    st.header("Visão de Calendário")

    leads_df = repository.get_detailed_leads()

    if leads_df.empty:
        st.warning("Não há leads para exibir.")
        return

    # Garantir que a coluna Prazo seja datetime e remover nulos para a comparação
    leads_df['Prazo'] = pd.to_datetime(leads_df['Prazo'], errors='coerce')
    leads_ativos = leads_df[
        (~leads_df['Etapa_Atual'].isin(['Concluído', 'Cancelado'])) & 
        (leads_df['Prazo'].notnull())
    ].copy()
    
    leads_ativos.sort_values(by='Prazo', inplace=True)

    # --- Seletor de Data ---
    # st.date_input retorna datetime.date se inicializado com datetime.date
    hoje_date = datetime.now().date()
    selected_date = st.date_input("Selecione uma data para ver os prazos", value=hoje_date)
    dias_para_visualizar = st.slider("Visualizar quantos dias a partir da data selecionada?", 1, 30, 7)
    
    data_inicio = selected_date
    data_fim = selected_date + timedelta(days=dias_para_visualizar - 1)

    # Filtragem segura comparando objetos date
    leads_filtrados = leads_ativos[
        (leads_ativos['Prazo'].dt.date >= data_inicio) & 
        (leads_ativos['Prazo'].dt.date <= data_fim)
    ]
        
    st.markdown("---")

    if leads_filtrados.empty:
        st.info(f"Nenhum lead ativo com prazo entre {data_inicio.strftime('%d/%m')} e {data_fim.strftime('%d/%m')}.")
    else:
        # Agrupa por data do prazo
        grouped_by_date = leads_filtrados.groupby(leads_filtrados['Prazo'].dt.date)
        
        for data, group in grouped_by_date:
            delta_dias = (data - datetime.now().date()).days
            if delta_dias == 0:
                header_text = f"Hoje ({data.strftime('%d/%m/%Y')})"
            elif delta_dias == 1:
                header_text = "Amanhã"
            elif delta_dias < 0:
                 header_text = f"Atrasado em {abs(delta_dias)} dias"
            else:
                header_text = f"Em {delta_dias} dias ({data.strftime('%d/%m/%Y')})"

            st.subheader(header_text, divider="gray")

            for _, lead in group.iterrows():
                status_indicator = utils.get_status_indicator(lead['Prazo'], lead['Status'])
                with st.container(border=True):
                    cols = st.columns([4, 2, 2])
                    cols[0].markdown(f"{status_indicator} **{lead.get('Nome_Contato', 'N/A')}** <br><small>Empresa: {lead.get('Razao_Social', 'N/A')}</small>", unsafe_allow_html=True)
                    cols[1].text(f"Responsável:\n{lead.get('Responsavel', 'N/A')}")
                    cols[2].text(f"Etapa Atual:\n{lead['Etapa_Atual']}")

                    with st.expander("Mais detalhes"):
                        st.write(f"**ID do Lead:** #{lead['ID_Lead']}")
                        if pd.notna(lead['Tags']) and lead['Tags']:
                            st.write(f"**Tags:** {lead['Tags']}")
                        st.caption("Para editar, acesse a visão Kanban.")

