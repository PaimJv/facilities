import streamlit as st
import pandas as pd
from utils import clean_data, get_yoy_data

def init_state():
    """
    Inicializa as variáveis de estado da sessão (Session State).
    O 'drill_path' armazena a hierarquia de navegação clicada pelo usuário.
    """
    if 'drill_path' not in st.session_state:
        st.session_state.drill_path = []

@st.cache_data(show_spinner="Processando base de dados...")
def load_and_process_base(files, apenas_completos):
    """
    Faz o carregamento, limpeza e preparação YoY dos dados.
    O uso do @st.cache_data garante que o re-processamento só ocorra 
    se os arquivos ou o modo de período mudarem.
    """
    try:
        # Consolida múltiplos CSVs em um único DataFrame
        # Nota: pd.read_csv usa sep=';' e encoding='latin-1' comum em exportações SAP/Excel
        # Altere APENAS esta linha dentro da função load_and_process_base:
        dfs = [clean_data(pd.read_csv(f, sep=';', encoding='utf-8-sig')) for f in files]
        full_df = pd.concat(dfs, ignore_index=True)
        
        # Gera a base comparativa Year-over-Year
        df_comp, ano_at, ano_ant = get_yoy_data(full_df, apenas_completos=apenas_completos)
        
        return df_comp, ano_at, ano_ant
    except Exception as e:
        # Retorna o erro como string para ser capturado pelo st.error no main.py
        return str(e), None, None

def voltar_nivel():
    """
    Remove o último nível da hierarquia de navegação (Breadcrumb).
    """
    if st.session_state.drill_path:
        st.session_state.drill_path.pop()

def apply_color_logic(val):
    """
    Lógica de Estilização Condicional (CSS) para o DataFrame.
    Regra de Facilities/Controladoria:
    - Valor Negativo (< 0): Redução de custo em relação ao ano anterior (Verde/Sucesso).
    - Valor Positivo (> 0): Aumento de custo em relação ao ano anterior (Vermelho/Atenção).
    """
    if isinstance(val, (int, float)):
        if val < 0:
            return 'background-color: #D4EDDA; color: #155724'  # Verde (Success)
        elif val > 0:
            return 'background-color: #F8D7DA; color: #721C24'  # Vermelho (Danger)
    return ''

def reset_navigation():
    """
    Limpa completamente o caminho de navegação, voltando ao topo da hierarquia.
    """
    st.session_state.drill_path = []