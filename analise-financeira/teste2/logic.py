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
    

def format_brl(val):
    """Formata valores para o padrão R$ 1.000,00 e R$ -1.000,00"""
    prefix = "R$ "
    if val < 0:
        val_abs = abs(val)
        return f"{prefix}-{val_abs:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{prefix}{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_trend_text(df_item):
    """Analisa a tendência sem asteriscos."""
    mensal = df_item.groupby('Mes')['Valor'].sum().sort_index()
    if len(mensal) < 2:
        return ""
    ultimos = mensal.tail(2).values
    if ultimos[-1] < ultimos[0]:
        reducao_pct = ((ultimos[0] - ultimos[-1]) / ultimos[0]) * 100 if ultimos[0] != 0 else 0
        return f" 📉 Tendência: Redução de {reducao_pct:.1f}% no último mês."
    return " 📈 Tendência: Elevação ou Estabilidade."

def prepare_report_data(df, dims, ano_at, ano_ant):
    """Pré-calcula todas as variações para evitar GroupBy dentro da recursão."""
    # Agrupamento global por todas as dimensões + Mes + Ano
    agrupado = df.groupby(dims + ['Mes', 'Ano'])['Valor'].sum().unstack(level='Ano').fillna(0)
    
    # Garante que os anos existem
    for a in [ano_at, ano_ant]:
        if a not in agrupado.columns: agrupado[a] = 0
    
    agrupado['Delta'] = agrupado[ano_at] - agrupado[ano_ant]
    return agrupado

def render_report_ui(df_master, dims, foco_res, profundidade=0, filtro_contexto=None):
    """Versão otimizada: consome a df_master pré-calculada."""
    if profundidade >= len(dims):
        return

    col = dims[profundidade]
    
    # Filtra a base mestra com base no que foi selecionado nos níveis acima
    df_nivel = df_master.copy()
    if filtro_contexto:
        for c, v in filtro_contexto.items():
            df_nivel = df_nivel.xs(v, level=c, drop_level=False)

    # Pega os itens únicos deste nível
    itens = sorted(df_nivel.index.get_level_values(col).unique().astype(str).tolist())

    # Dicionário de meses (estático para performance)
    meses_nomes = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun',
                   7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}

    for item in itens:
        # Dados do item atual
        df_item = df_nivel.xs(item, level=col, drop_level=False)
        var_total = df_item['Delta'].sum()
        
        # Lógica de Materialidade (R$ 1.000,00)
        def meets_foco(val):
            if abs(val) < 1000: return False
            return val < 0 if "Savings" in foco_res else (val > 0 if "Desvios" in foco_res else True)

        # Checagem rápida de subclasses (sem novo groupby)
        sub_impacto = False
        if profundidade < len(dims) - 1:
            sub_impacto = df_item['Delta'].groupby(level=dims[-1]).sum().apply(meets_foco).any()

        if meets_foco(var_total) or sub_impacto:
            tipo = "💰 SAVING" if var_total < 0 else "⚠️ DESVIO"
            label = f"{'📌' if profundidade == 0 else '➥'} {item} | Total: {format_brl(var_total)}"
            
            with st.expander(label):
                # Detalhamento mensal usando a df_item já filtrada
                delta_mensal = df_item.groupby(level='Mes')['Delta'].sum()
                meses_atuais = delta_mensal.index.tolist()
                cols = st.columns(len(meses_atuais))
                
                for idx, m_num in enumerate(meses_atuais):
                    with cols[idx]:
                        st.caption(meses_nomes.get(m_num))
                        st.write(format_brl(delta_mensal[m_num]))

                # Recursão passando o novo contexto de filtro
                novo_contexto = (filtro_contexto or {}).copy()
                novo_contexto[col] = item
                render_report_ui(df_master, dims, foco_res, profundidade + 1, novo_contexto)