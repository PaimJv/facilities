import pandas as pd
import streamlit as st

@st.cache_data(show_spinner=False)
def clean_data(df):
    """
    Limpeza ultra-robusta com Cache. 
    Identifica 'Cl.custo' e garante que a hierarquia seja processada sem duplicidade.
    """
    # 1. Limpeza de nomes de colunas
    df.columns = [c.strip() for c in df.columns]
    
    # 2. Mapeamento inteligente (Keywords)
    mapeado = {k: False for k in ['Classe_Custo', 'Centro_Custo', 'Localidade', 'Diretoria', 'VP', 'Texto_Material', 
                                  'Valor_Original', 'Data_Lancamento']}
    
    new_cols = {}
    for col in df.columns:
        c_upper = col.upper()
        
        # Prioridade de mapeamento
        if 'LOCAL' in c_upper and not mapeado['Localidade']: 
            new_cols[col] = 'Localidade'; mapeado['Localidade'] = True
        elif 'DIRET' in c_upper and not mapeado['Diretoria']: 
            new_cols[col] = 'Diretoria'; mapeado['Diretoria'] = True
        elif 'VP' in c_upper and not mapeado['VP']: 
            new_cols[col] = 'VP'; mapeado['VP'] = True
        elif 'TEXTO' in c_upper and 'MAT' in c_upper and not mapeado['Texto_Material']: 
            new_cols[col] = 'Texto_Material'; mapeado['Texto_Material'] = True
        elif 'VALOR' in c_upper and not mapeado['Valor_Original']: 
            new_cols[col] = 'Valor_Original'; mapeado['Valor_Original'] = True
        elif 'DT' in c_upper and 'TO' in c_upper and not mapeado['Data_Lancamento']: 
            new_cols[col] = 'Data_Lancamento'; mapeado['Data_Lancamento'] = True
        
        # Identificação específica para Classe de Custo (Cl.custo)
        elif ('CL.' in c_upper or 'CLASSE' in c_upper or 'CONTA' in c_upper) and not mapeado['Classe_Custo']: 
            new_cols[col] = 'Classe_Custo'; mapeado['Classe_Custo'] = True
            
        elif 'CENTRO' in c_upper and 'CST' in c_upper and not mapeado['Centro_Custo']: 
            new_cols[col] = 'Centro_Custo'; mapeado['Centro_Custo'] = True
            
    df = df.rename(columns=new_cols).copy()

    # 3. Blindagem contra colunas duplicadas
    df = df.loc[:, ~df.columns.duplicated()]

    # 4. Filtro VP = 0
    if 'VP' in df.columns:
        df = df[df['VP'].astype(str).str.strip() != '0']

    # 5. Padronização de Strings (Evita erros no sorted e selectbox)
    cols_to_fix = ['Localidade', 'Diretoria', 'VP', 'Texto_Material', 'Classe_Custo', 'Centro_Custo']
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = df[col].astype(str).replace('nan', 'Não Informado').str.strip()

    # 6. Conversão de Valor (Suporta ponto como milhar e vírgula como decimal)
    if 'Valor_Original' in df.columns:
        v_col = df['Valor_Original']
        if v_col.dtype == object:
            df['Valor'] = (v_col.str.replace('.', '', regex=False)
                           .str.replace(',', '.', regex=False)
                           .astype(float))
        else:
            df['Valor'] = v_col
    
    # 7. Parsing de Datas e Atributos Temporais
    df['Data_Lancamento'] = pd.to_datetime(df['Data_Lancamento'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Data_Lancamento'])
    
    df['Dia'] = df['Data_Lancamento'].dt.day
    df['Mes'] = df['Data_Lancamento'].dt.month
    df['Ano'] = df['Data_Lancamento'].dt.year
    
    return df

@st.cache_data(show_spinner=False)
def get_yoy_data(full_df, apenas_completos=False):
    """
    Filtra períodos equivalentes para comparação justa (YoY).
    Cacheado para evitar reprocessamento em cada clique de navegação.
    """
    if full_df.empty:
        return full_df, None, None
        
    ano_atual = full_df['Ano'].max()
    ano_anterior = full_df['Ano'].min()
    
    # Busca a última data do ano atual para servir de régua para o ano anterior
    ultima_data = full_df[full_df['Ano'] == ano_atual]['Data_Lancamento'].max()
    
    if apenas_completos:
        # Filtra apenas meses que já terminaram no ano atual
        df_comp = full_df[full_df['Mes'] < ultima_data.month]
    else:
        # Filtra até o dia/mês exato da última atualização
        df_comp = full_df[
            (full_df['Mes'] < ultima_data.month) | 
            ((full_df['Mes'] == ultima_data.month) & (full_df['Dia'] <= ultima_data.day))
        ]
        
    return df_comp, ano_atual, ano_anterior