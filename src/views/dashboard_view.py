# dashboard_view.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from data import repository_excel as repository
import config

def display():
    """
    Exibe a página de Dashboard com métricas e gráficos sobre os leads.
    """
    st.header("📊 Dashboard Operacional")

    try:
        leads_df = repository.get_detailed_leads()
        historico_df = repository.get_all('Historico')
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados: {e}")
        return

    if leads_df.empty:
        st.warning("Não há dados de leads para gerar métricas.")
        return

    # --- Pré-processamento ---
    hoje = datetime.now()
    mes_atual = hoje.month
    ano_atual = hoje.year

    # Garantir que colunas de data são do tipo datetime
    for col in ['Prazo', 'Ultima_Atualizacao', 'Data_Criacao', 'Data_Entrada_Etapa']:
        if col in leads_df.columns:
            leads_df[col] = pd.to_datetime(leads_df[col], errors='coerce')

    # Definição de estágios para métricas
    all_stages = config.ETAPAS_KANBAN
    qualified_stages = ["Propostas", "Reuniões", "Negociação", "Ganhos"]
    
    # --- KPIs Principais ---
    st.subheader("Indicadores Chave (Mês Atual)", divider="blue")

    total_leads = len(leads_df)
    new_leads_month = len(leads_df[
        (leads_df['Data_Criacao'].dt.month == mes_atual) &
        (leads_df['Data_Criacao'].dt.year == ano_atual)
    ])
    
    leads_qualificados = leads_df[leads_df['Etapa_Atual'].isin(qualified_stages)]
    percent_qualificados = (len(leads_qualificados) / total_leads) * 100 if total_leads > 0 else 0
    
    vendas_concluidas = len(leads_df[leads_df['Etapa_Atual'] == "Ganhos"])

    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Total de Leads", total_leads)
    kpi_cols[1].metric("Novos no Mês", new_leads_month)
    kpi_cols[2].metric("% Qualificados", f"{percent_qualificados:.1f}%")
    kpi_cols[3].metric("Vendas (Ganhos)", vendas_concluidas)
    
    st.markdown("---")

    # --- Gráficos ---
    st.subheader("Análises Visuais", divider="blue")
    
    chart_cols_top = st.columns(2)

    with chart_cols_top[0]:
        # Gráfico: Leads por Etapa
        st.write("#### Volume por Etapa do Funil")
        etapas_counts = leads_df['Etapa_Atual'].value_counts().reindex(all_stages, fill_value=0).reset_index()
        etapas_counts.columns = ['Etapa', 'Quantidade']
        fig1 = px.bar(etapas_counts, x='Etapa', y='Quantidade', color='Etapa', color_discrete_sequence=px.colors.qualitative.Prism)
        st.plotly_chart(fig1, use_container_width=True)

    with chart_cols_top[1]:
        # Gráfico de Pizza: Distribuição por Prioridade
        st.write("#### Distribuição por Prioridade")
        prio_data = leads_df['Prioridade'].value_counts().reset_index()
        prio_data.columns = ['Prioridade', 'Quantidade']
        fig2 = px.pie(prio_data, names='Prioridade', values='Quantidade', hole=.4, color='Prioridade',
                      color_discrete_map={'Alta': '#ff4b4b', 'Média': '#ffa500', 'Baixa': '#28a745'})
        st.plotly_chart(fig2, use_container_width=True)

    chart_cols_bottom = st.columns(2)
    
    with chart_cols_bottom[0]:
        # Gráfico: Leads por Núcleo
        st.write("#### Leads por Núcleo")
        if 'Nucleo' in leads_df.columns:
            nucleo_counts = leads_df['Nucleo'].value_counts().reset_index()
            nucleo_counts.columns = ['Núcleo', 'Quantidade']
            fig3 = px.bar(nucleo_counts, x='Núcleo', y='Quantidade', orientation='v')
            st.plotly_chart(fig3, use_container_width=True)

    with chart_cols_bottom[1]:
        # SLA Atual (Média de dias na etapa)
        st.write("#### SLA: Média de Dias na Etapa Atual")
        leads_df['Dias_na_Etapa'] = (datetime.now() - leads_df['Data_Entrada_Etapa']).dt.days
        avg_sla = leads_df.groupby('Etapa_Atual')['Dias_na_Etapa'].mean().reindex(all_stages, fill_value=0).reset_index()
        avg_sla.columns = ['Etapa', 'Dias']
        fig4 = px.line(avg_sla, x='Etapa', y='Dias', markers=True)
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")

    # Visão Analítica / Tabela de Leads
    st.subheader("Visão Analítica Detalhada", divider="blue")
    display_cols = ['ID_Lead', 'Razao_Social', 'Nome_Contato', 'Telefone', 'Etapa_Atual', 'Prioridade', 'Data_Criacao']
    st.dataframe(leads_df[display_cols], use_container_width=True)
