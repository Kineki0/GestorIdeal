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
    st.header("Dashboard Gerencial de Leads")

    try:
        leads_df = repository.get_detailed_leads()
        historico_df = repository.get_all('Historico')
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar os dados: {e}")
        return

    if leads_df.empty:
        st.warning("Não há dados de leads para gerar métricas.")
        return

    # --- Pré-processamento e Métricas Comuns ---
    hoje = datetime.now()
    mes_atual = hoje.month
    ano_atual = hoje.year

    # Garantir que colunas de data são do tipo datetime
    for col in ['Prazo', 'Ultima_Atualizacao', 'Data_Criacao']:
        leads_df[col] = pd.to_datetime(leads_df[col], errors='coerce')

    # --- KPIs Principais ---
    st.subheader("Indicadores Chave", divider="blue")

    total_leads_mes = len(leads_df[
        (leads_df['Data_Criacao'].dt.month == mes_atual) &
        (leads_df['Data_Criacao'].dt.year == ano_atual)
    ])
    
    total_leads = len(leads_df)
    
    qualified_stages = config.ETAPAS_QUALIFICADO
    leads_qualificados = leads_df[leads_df['Etapa_Atual'].isin(qualified_stages)]
    percent_leads_qualificados = (len(leads_qualificados) / total_leads) * 100 if total_leads > 0 else 0

    # Tempo médio para qualificação
    qualified_this_month = leads_qualificados[
        (leads_qualificados['Ultima_Atualizacao'].dt.month == mes_atual) &
        (leads_qualificados['Ultima_Atualizacao'].dt.year == ano_atual)
    ]
    
    avg_time_to_qualify_days = "N/A"
    if not qualified_this_month.empty:
        qualified_this_month = qualified_this_month.copy()
        qualified_this_month['Tempo_Qualificacao'] = (qualified_this_month['Ultima_Atualizacao'] - qualified_this_month['Data_Criacao']).dt.days
        avg_time_to_qualify_days = qualified_this_month['Tempo_Qualificacao'].mean()
        avg_time_to_qualify_days = f"{avg_time_to_qualify_days:.1f}"


    hot_leads = leads_df[
        (leads_df['Etapa_Atual'].isin(qualified_stages)) &
        (leads_df['Prioridade'] == 'Alta')
    ]

    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Total de Leads", total_leads)
    kpi_cols[1].metric("Novos Leads no Mês", total_leads_mes)
    kpi_cols[2].metric("% de Leads Qualificados", f"{percent_leads_qualificados:.1f}%")
    kpi_cols[3].metric("Leads Quentes", len(hot_leads))
    
    kpi_cols2 = st.columns(4)
    kpi_cols2[0].metric("Tempo Médio de Qualificação (dias)", avg_time_to_qualify_days)
    # Placeholder for other KPIs
    kpi_cols2[1].metric("Contatos Agendados Mês", "N/A") # Placeholder
    kpi_cols2[2].metric("Leads por Operador", "N/A") # Placeholder
    kpi_cols2[3].metric("Total de Leads este Mês", total_leads_mes)
    
    st.markdown("---")

    # --- Gráficos ---
    st.subheader("Análises Visuais", divider="blue")
    
    chart_cols_top = st.columns(2)

    with chart_cols_top[0]:
        # Gráfico de Pizza: Distribuição de Leads por fase até follow up
        st.write("#### Distribuição de Leads por Fase (Até Follow-up)")
        etapas_ate_followup = config.ETAPAS_ATIVAS[:config.ETAPAS_ATIVAS.index("Follow-up") + 1]
        leads_ate_followup = leads_df[leads_df['Etapa_Atual'].isin(etapas_ate_followup)]
        if not leads_ate_followup.empty:
            pie_data = leads_ate_followup['Etapa_Atual'].value_counts().reset_index()
            pie_data.columns = ['Etapa', 'Quantidade']
            fig = px.pie(pie_data, names='Etapa', values='Quantidade', title="Leads por Fase", hole=.3)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum lead encontrado nas etapas até Follow-up.")

    with chart_cols_top[1]:
        # Gráfico de Pizza: Distribuição de Leads por fase - qualificado
        st.write("#### Distribuição de Leads Qualificados")
        if not leads_qualificados.empty:
            pie_data_qualified = leads_qualificados['Etapa_Atual'].value_counts().reset_index()
            pie_data_qualified.columns = ['Etapa', 'Quantidade']
            fig2 = px.pie(pie_data_qualified, names='Etapa', values='Quantidade', title="Leads Qualificados", hole=.3)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nenhum lead qualificado encontrado.")

    # Gráfico de Barras: Leads por Etapa
    st.write("#### Leads por Etapa (Geral)")
    etapas_counts = leads_df['Etapa_Atual'].value_counts().reindex(repository.get_kanban_stages(), fill_value=0).reset_index()
    etapas_counts.columns = ['Etapa', 'Quantidade']
    fig3 = px.bar(etapas_counts, x='Etapa', y='Quantidade', title="Volume de Leads por Etapa do Funil")
    st.plotly_chart(fig3, use_container_width=True)

    
    chart_cols_bottom = st.columns(2)
    with chart_cols_bottom[0]:
        # Gráfico de Barras: Leads por Indústria
        st.write("#### Leads por Indústria")
        if 'Industria' in leads_df.columns and not leads_df['Industria'].isnull().all():
            industria_counts = leads_df['Industria'].value_counts().reset_index()
            industria_counts.columns = ['Industria', 'Quantidade']
            fig4 = px.bar(industria_counts, x='Industria', y='Quantidade', title="Leads por Segmento de Mercado")
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Dados de Indústria não disponíveis ou vazios.")

    with chart_cols_bottom[1]:
        # Gráfico de Barras: Leads por Operador
        st.write("#### Leads por Operador")
        # Assuming 'Responsavel' column exists. If not, this needs adjustment.
        if 'Responsavel' in leads_df.columns and not leads_df['Responsavel'].isnull().all():
            operador_counts = leads_df['Responsavel'].value_counts().reset_index()
            operador_counts.columns = ['Operador', 'Quantidade']
            fig5 = px.bar(operador_counts, x='Operador', y='Quantidade', title="Leads por Membro da Equipe")
            st.plotly_chart(fig5, use_container_width=True)
        else:
            # Fallback to User from history if 'Responsavel' doesn't exist on lead
            if not historico_df.empty:
                # Get the last user to modify the lead as a proxy for the owner
                last_touch_df = historico_df.sort_values('Timestamp').drop_duplicates('ID_Lead', keep='last')
                owner_counts = last_touch_df['Usuario'].value_counts().reset_index()
                owner_counts.columns = ['Operador', 'Quantidade']
                fig5 = px.bar(owner_counts, x='Operador', y='Quantidade', title="Leads por Último Operador (do Histórico)")
                st.plotly_chart(fig5, use_container_width=True)
            else:
                st.info("Dados de Responsável/Operador não disponíveis.")

    # Tempo Médio por Fase (SLA)
    st.write("#### Tempo Médio por Fase (Dias)")
    # Usar a coluna Data_Entrada_Etapa se disponível para calcular o tempo atual na fase
    leads_df['Dias_na_Etapa'] = (datetime.now() - pd.to_datetime(leads_df['Data_Entrada_Etapa'])).dt.days
    
    avg_sla_per_stage = leads_df.groupby('Etapa_Atual')['Dias_na_Etapa'].mean().reindex(repository.get_kanban_stages(), fill_value=0).reset_index()
    avg_sla_per_stage.columns = ['Etapa', 'Média de Dias']
    
    fig6 = px.bar(avg_sla_per_stage, x='Etapa', y='Média de Dias', title="SLA Atual: Tempo Médio que os Leads estão parados em cada etapa")
    st.plotly_chart(fig6, use_container_width=True)

    st.markdown("---")

    # Visão Analítica / Tabela de Leads
    st.subheader("Visão Analítica de Leads", divider="blue")
    # Add 'Responsavel' if it exists, otherwise it will be ignored by st.dataframe
    display_cols = ['ID_Lead', 'Razao_Social', 'Nome_Contato', 'Etapa_Atual', 'Status', 'Prioridade', 'Prazo', 'Data_Criacao']
    if 'Responsavel' in leads_df.columns:
        display_cols.append('Responsavel')
    
    st.dataframe(leads_df[display_cols], use_container_width=True)

