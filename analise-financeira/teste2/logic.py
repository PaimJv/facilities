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
    """Pre-calcula os dados garantindo que nenhum valor seja descartado (Lossless)."""
    # Lista de todas as colunas possíveis da hierarquia
    todas_cols = ['Desc_Conta', 'P_L', 'VP', 'Localidade', 'Centro_Custo', 'Desc_Material']
    
    # Criamos uma cópia para não afetar o DataFrame original do main
    df_clean = df.copy()
    
    # CRÍTICO: Preenchemos valores nulos com uma string para o groupby não descartar linhas
    for c in todas_cols:
        if c in df_clean.columns:
            df_clean[c] = df_clean[c].fillna("Não Informado").astype(str)
    
    # Agrupamento global usando dropna=False por segurança extra
    agrupado = df_clean.groupby(dims + ['Mes', 'Ano'], dropna=False)['Valor'].sum().unstack(level='Ano').fillna(0)
    
    for a in [ano_at, ano_ant]:
        if a not in agrupado.columns: agrupado[a] = 0
    
    agrupado['Delta'] = agrupado[ano_at] - agrupado[ano_ant]
    return agrupado

def render_report_ui(df_master, dims, ano_at, ano_ant, foco_res, profundidade=0, filtro_contexto=None):
    """Relatório onde o Material é puramente informativo e os totais são preservados."""
    if profundidade >= len(dims):
        return

    meses_nomes = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun',
                   7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}

    col = dims[profundidade]
    
    # Filtra a base master conforme o nível atual
    df_nivel = df_master.copy()
    if filtro_contexto:
        for c, v in filtro_contexto.items():
            df_nivel = df_nivel.xs(v, level=c, drop_level=False)

    # --- 🟢 NÍVEL FINAL: MATERIAIS (APENAS OBSERVAÇÃO) ---
    if col == 'Desc_Material':
        st.markdown(f"#### 📦 Balanço Detalhado de Objetos")
        
        # Agrupamos por Mês e Material pegando TUDO do contexto atual
        df_mat_mes = df_nivel.groupby(['Mes', 'Desc_Material'])[[ano_ant, ano_at]].sum()
        
        for m_num in sorted(df_mat_mes.index.get_level_values('Mes').unique()):
            st.write(f"📅 **Referência: {meses_nomes.get(m_num)}**")
            
            df_exibir = df_mat_mes.xs(m_num, level='Mes').copy()
            df_exibir.index.name = "Objeto"
            df_exibir.columns = pd.MultiIndex.from_tuples([(str(ano_ant), "Valor"), (str(ano_at), "Valor")])
            
            # Totais do mês vindos do contexto pai (para garantir fidelidade)
            t_ant = df_exibir[(str(ano_ant), "Valor")].replace(r'[R$\s.]', '', regex=True).replace(',', '.', regex=True).astype(float).sum() if df_exibir.empty else df_mat_mes.xs(m_num, level='Mes')[ano_ant].sum()
            t_at = df_mat_mes.xs(m_num, level='Mes')[ano_at].sum()
            t_ant = df_mat_mes.xs(m_num, level='Mes')[ano_ant].sum()

            df_total = pd.DataFrame([[format_brl(t_ant), format_brl(t_at)]], 
                                    columns=df_exibir.columns, index=["Total Contexto"])
            
            st.table(pd.concat([df_exibir.map(format_brl), df_total]))
        return 

    # --- 🔵 NÍVEIS DE GESTÃO (CONTA, LOCALIDADE, CC, ETC) ---
    itens = sorted(df_nivel.index.get_level_values(col).unique().astype(str).tolist())

    for item in itens:
        df_item = df_nivel.xs(item, level=col, drop_level=False)
        var_total = df_item['Delta'].sum()
        
        def meets_foco(val):
            if abs(val) < 1000: return False
            if "Savings" in foco_res: return val < 0
            if "Desvios" in foco_res: return val > 0
            return True

        # Verifica se há economia real nas subclasses (excluindo material da decisão de abrir expander)
        sub_impacto = False
        if profundidade < len(dims) - 1 and dims[profundidade+1] != 'Desc_Material':
            sub_impacto = df_item['Delta'].groupby(level=dims[profundidade+1]).sum().apply(meets_foco).any()

        if meets_foco(var_total) or sub_impacto:
            label = f"{'📌' if profundidade == 0 else '➥'} {item} | Total Período: {format_brl(var_total)}"
            
            with st.expander(label):
                st.write("**Variação Mensal YoY (Impacto no Resultado):**")
                delta_mensal = df_item.groupby(level='Mes')['Delta'].sum()
                cols = st.columns(len(delta_mensal))
                for idx, m_num in enumerate(delta_mensal.index):
                    with cols[idx]:
                        st.caption(meses_nomes.get(m_num))
                        st.write(format_brl(delta_mensal[m_num]))

                st.divider()
                novo_contexto = (filtro_contexto or {}).copy()
                novo_contexto[col] = item
                render_report_ui(df_master, dims, ano_at, ano_ant, foco_res, profundidade + 1, novo_contexto)