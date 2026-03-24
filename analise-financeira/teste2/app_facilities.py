import streamlit as st
import pandas as pd
import plotly.express as px
from google import genai

# Configuração do Gemini
# Substitua pela sua chave de API ou use segredos do Streamlit
client = genai.Client(api_key="AIzaSyC7VzUUb4Bq4OWfiaRVCgHQNQ1UqA5k2_E")

def clean_data(df):
    # Remove espaços extras nos nomes das colunas
    df.columns = [c.strip() for c in df.columns]
    
    # Dicionário de tradução: (O que pode vir no Excel) -> (Como chamaremos no código)
    mapa_colunas = {
        'Dt.lçto.': 'Data_Lancamento',
        'Dt.lÃ§to.': 'Data_Lancamento', # Caso venha com erro de encoding
        'Valor/moeda objeto': 'Valor_Original',
        'Texto breve material': 'Texto_Material',
        'LOCALIDADE': 'Localidade',
        'DIRETORIA': 'Diretoria',
        'VP': 'VP',
        'LINHA P&L': 'Linha_PL',
        'Centro cst': 'Centro_Custo'
    }
    
    # Renomeia apenas as colunas que existirem no arquivo
    df = df.rename(columns=mapa_colunas)

    # Tratamento do Valor (Converte "1.234,56" para 1234.56)
    if 'Valor_Original' in df.columns:
        if df['Valor_Original'].dtype == object:
            df['Valor'] = df['Valor_Original'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
        else:
            df['Valor'] = df['Valor_Original']
    
    # Tratamento da Data
    col_data = 'Data_Lancamento'
    df[col_data] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
    df = df.dropna(subset=[col_data])
    
    df['Mes'] = df[col_data].dt.month
    df['Ano'] = df[col_data].dt.year
    
    return df

def generate_ai_insights(data_summary, context_text):
    """Gera insights utilizando a nova SDK e o modelo Gemini 2.0 Flash"""
    prompt = f"""
    Como um Analista de Dados Sênior, analise os seguintes dados de custos de Facilities:
    {data_summary}
    
    Contexto do Cliente: {context_text}
    
    Identifique onde há 'produtividade' (redução de custo real). 
    Procure por gastos não recorrentes (ex: compra de materiais duráveis como portas, reformas) que justificam a variação.
    Gere um relatório executivo curto focando em onde o gestor deve atuar.
    """
    
    # Chamada atualizada para o modelo Gemini 2.0 Flash
    response = client.models.generate_content(
        model="gemini-2.0-flash", 
        contents=prompt
    )
    return response.text

# --- Interface Streamlit ---
st.set_page_config(page_title="Dashboard Facilities YoY", layout="wide")
st.title("📊 Análise de Produtividade - Facilities")

uploaded_files = st.file_uploader("Anexe os arquivos CSV (ex: 2025 e 2026)", accept_multiple_files=True)

if len(uploaded_files) >= 2:
    data_frames = []
    for file in uploaded_files:
        df_raw = pd.read_csv(file, sep=';', encoding='latin-1')
        data_frames.append(clean_data(df_raw))
    
    full_df = pd.concat(data_frames)
    
    # Identificar anos e filtrar meses comparáveis
    anos = sorted(full_df['Ano'].unique())
    ano_atual = anos[-1]
    ano_anterior = anos[-2]
    
    meses_disponiveis_atual = full_df[full_df['Ano'] == ano_atual]['Mes'].unique()
    df_comp = full_df[full_df['Mes'].isin(meses_disponiveis_atual)]
    
    # 1. Visão Geral YoY por Mês
    st.header(f"Comparativo Mensal: {ano_anterior} vs {ano_atual}")
    yoy_month = df_comp.groupby(['Ano', 'Mes'])['Valor'].sum().reset_index()
    fig_month = px.bar(yoy_month, x='Mes', y='Valor', color='Ano', barmode='group', 
                       title="Custo Total por Mês (Meses Comparáveis)")
    st.plotly_chart(fig_month, use_container_width=True)

    # 2. O "Funil" de Produtividade
    st.header("🔍 Afunilamento de Dados")
    col1, col2, col3 = st.columns(3)

    with col1:
        # Usamos os nomes novos que definimos no rename_map
        opcoes_dimensao = {
            'VP': 'VP',
            'Diretoria': 'Diretoria',
            'Localidade': 'Localidade',
            'Classe de Custo': 'Classe_Custo',
            'Linha P&L': 'Linha_PL',
            'Centro de Custo': 'Centro_Custo_ID'
        }
        selecao_usuario = st.selectbox("Selecione a Dimensão de Análise", list(opcoes_dimensao.keys()))
        dimensao = opcoes_dimensao[selecao_usuario]
    
    # Cálculo de variação por dimensão
    analysis = df_comp.groupby(['Ano', dimensao])['Valor'].sum().unstack(level=0).fillna(0)
    analysis['Variacao_Absoluta'] = analysis[ano_atual] - analysis[ano_anterior]
    analysis['Variacao_Percentual'] = (analysis['Variacao_Absoluta'] / analysis[ano_anterior]) * 100
    
    st.subheader(f"Variação por {dimensao}")
    st.write(analysis.sort_values(by='Variacao_Absoluta'))

    # 3. Visão de Material (Abaixo do Funil)
    st.header("📦 Análise por Material/Descrição")

    # Aqui garantimos que o filtro de VP use o nome correto
    vps_disponiveis = sorted(df_comp['VP'].unique())
    vp_selecionada = st.selectbox("Filtrar VP específica para ver materiais:", vps_disponiveis)

    # Filtra os dados pela VP escolhida
    detalhe_material = df_comp[df_comp['VP'] == vp_selecionada]

    # CORREÇÃO AQUI: Usamos 'Texto_Material' em vez de 'Texto breve material'
    mat_summary = (detalhe_material.groupby(['Ano', 'Texto_Material'])['Valor']
                .sum()
                .unstack(level=0)
                .fillna(0))

    # Adiciona uma coluna de variação para ajudar o Ítalo a ver a "produtividade"
    if len(mat_summary.columns) >= 2:
        anos_cols = sorted(mat_summary.columns)
        mat_summary['Variacao_Absoluta'] = mat_summary[anos_cols[-1]] - mat_summary[anos_cols[-2]]
        st.dataframe(mat_summary.sort_values(by='Variacao_Absoluta'))
    else:
        st.dataframe(mat_summary)

    # 4. Insights da IA
    if st.button("Gerar Insights com AI (Gemini)"):
        with st.spinner("Analisando dados..."):
            resumo_texto = analysis.sort_values(by='Variacao_Absoluta').head(10).to_string()
            insights = generate_ai_insights(resumo_texto, "Buscando produtividade em Facilities e gastos não recorrentes.")
            st.info(insights)

else:
    st.warning("Por favor, anexe pelo menos dois arquivos de anos diferentes para comparação.")