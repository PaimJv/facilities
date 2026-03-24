import plotly.express as px
import pandas as pd
import streamlit as st

def plot_yoy_chart(df_comp):
    """
    Gera um gráfico de barras comparativo mensal simples para o custo total.
    Ideal para uma visão macro de sazonalidade entre os anos.
    """
    resumo = df_comp.groupby(['Ano', 'Mes'])['Valor'].sum().reset_index()
    
    fig = px.bar(
        resumo, 
        x='Mes', 
        y='Valor', 
        color='Ano', 
        barmode='group',
        title="📊 Comparativo de Custos Totais Mensais (Período Equivalente)",
        labels={'Valor': 'Custo Total (R$)', 'Mes': 'Mês', 'Ano': 'Ano'}
    )
    
    # Configuração de eixos e formato de moeda (BR)
    fig.update_layout(
        xaxis_type='category', 
        separators=',.', 
        yaxis=dict(tickformat=',.2f')
    )
    return fig

def plot_drilldown_chart(df, level_col, ano_atual, ano_anterior):
    """
    Gráfico de impacto financeiro (Variação Absoluta).
    Utiliza escala divergente com o zero como ponto central (Midpoint).
    """
    # Consolidação dos anos para cálculo da diferença
    pivot = df.groupby(['Ano', level_col])['Valor'].sum().unstack(level=0).fillna(0)
    
    # Garantia de que as colunas existem para evitar KeyError
    for ano in [ano_atual, ano_anterior]:
        if ano not in pivot.columns:
            pivot[ano] = 0
            
    # Cálculo da Variação (Saving se negativo, Gasto se positivo)
    pivot['Variacao'] = pivot[ano_atual] - pivot[ano_anterior]
    pivot = pivot.sort_values(by='Variacao').reset_index()
    
    # Construção do gráfico
    fig = px.bar(
        pivot, 
        x=level_col, 
        y='Variacao',
        title=f"📉 Impacto Financeiro YoY por {level_col}",
        labels={'Variacao': 'Diferença YoY (R$)', level_col: level_col},
        color='Variacao',
        # RdYlGn_r: Red (Gasto) -> Yellow (Neutro) -> Green (Saving)
        color_continuous_scale='RdYlGn_r', 
        color_continuous_midpoint=0,  # CRÍTICO: Fixa o zero como cor neutra
        text_auto='.2s'
    )
    
    # Formatação visual
    fig.update_layout(
        separators=',.', 
        yaxis=dict(tickformat=',.2f'),
        coloraxis_showscale=True
    )
    return fig

def render_dynamic_table(df, level_col, ano_atual, ano_anterior):
    """
    Gera a matriz (pivot) de variação mensal para a tabela dinâmica.
    Calcula (Ano Atual - Ano Anterior) para cada célula da matriz.
    """
    # 1. Pivotar Ano Atual
    p_atual = df[df['Ano'] == ano_atual].pivot_table(
        index=level_col, columns='Mes', values='Valor', aggfunc='sum'
    ).fillna(0)
    
    # 2. Pivotar Ano Anterior
    p_ant = df[df['Ano'] == ano_anterior].pivot_table(
        index=level_col, columns='Mes', values='Valor', aggfunc='sum'
    ).fillna(0)
    
    # 3. Sincronizar eixos para garantir que a subtração ocorra em meses equivalentes
    todos_meses = sorted(list(set(p_atual.columns) | set(p_ant.columns)))
    p_atual = p_atual.reindex(columns=todos_meses, fill_value=0)
    p_ant = p_ant.reindex(columns=todos_meses, fill_value=0)
    
    # 4. Cálculo da Diferença (Deltas Mensais)
    df_yoy = p_atual - p_ant
    
    # 5. Adição de métrica acumulada no final
    df_yoy['Total Geral'] = df_yoy.sum(axis=1)
    
    # 6. Mapeamento de meses para formato legível (BR)
    meses_br = {
        1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun',
        7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'
    }
    df_yoy.columns = [meses_br.get(c, c) for c in df_yoy.columns]
    
    # Retorna ordenado pelo maior "ofensor" (maior custo incremental)
    return df_yoy.sort_values(by='Total Geral', ascending=False)