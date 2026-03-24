import streamlit as st
import pandas as pd
from utils import clean_data, get_yoy_data
from ia_engine import get_ai_insights
from components import plot_drilldown_chart, render_dynamic_table

# --- 1. CONFIGURAÇÃO DA INTERFACE ---
st.set_page_config(
    page_title="Auditoria Avançada Facilities",
    page_icon="🕵️‍♂️",
    layout="wide"
)

# --- 2. ACESSO SEGURO (API KEY) ---
@st.cache_resource
def get_api_key():
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return None

api_key = get_api_key()
if not api_key:
    st.error("❌ Erro: 'GROQ_API_KEY' não encontrada no ficheiro secrets.toml.")
    st.stop()

# --- 3. MOTOR DE PROCESSAMENTO (CACHE) ---
@st.cache_data(show_spinner=False)
def load_and_process_base(files, apenas_completos):
    """Carregamento e limpeza inicial dos dados."""
    try:
        dfs = [clean_data(pd.read_csv(f, sep=';', encoding='latin-1')) for f in files]
        full_df = pd.concat(dfs, ignore_index=True)
        return get_yoy_data(full_df, apenas_completos=apenas_completos)
    except Exception as e:
        return e, None, None

# --- 4. GESTÃO DE ESTADO E NAVEGAÇÃO ---
if 'drill_path' not in st.session_state:
    st.session_state.drill_path = []

def voltar_nivel():
    if st.session_state.drill_path:
        st.session_state.drill_path.pop()

# Lógica de cores direta (Verde para Savings, Vermelho para Desvios)
def apply_color_logic(val):
    if isinstance(val, (int, float)):
        if val < 0: return 'background-color: #D4EDDA; color: #155724'
        elif val > 0: return 'background-color: #F8D7DA; color: #721C24'
    return ''

# --- 5. PAINEL DE FILTROS (SIDEBAR) ---
st.sidebar.title("🔍 Parâmetros da Auditoria")
st.sidebar.markdown("---")

uploaded_files = st.sidebar.file_uploader(
    "1. Base de Dados (CSVs):", 
    accept_multiple_files=True, 
    type=["csv"]
)

if len(uploaded_files) >= 2:
    # Processamento base para liberar filtros dinâmicos
    df_raw, ano_at, ano_ant = load_and_process_base(uploaded_files, False)
    
    if isinstance(df_raw, Exception):
        st.sidebar.error("Erro nos arquivos.")
        st.stop()

    # FILTRO: Meses Disponíveis
    meses_lista = sorted(df_raw['Mes'].unique())
    meses_br = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun',
                7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}
    
    selecao_meses = st.sidebar.multiselect(
        "2. Período (Meses):", 
        options=meses_lista, 
        default=meses_lista,
        format_func=lambda x: meses_br.get(x, x)
    )

    # FILTRO: Dimensões para o Relatório de IA
    dimensoes_ia = st.sidebar.multiselect(
        "3. Dimensões para a IA (Contas):",
        ['Classe_Custo', 'Centro_Custo', 'Localidade', 'Diretoria', 'VP'],
        default=['Localidade', 'Classe_Custo']
    )

    # FILTRO: Foco do Resultado
    foco_resultado = st.sidebar.radio(
        "4. Foco da Análise:",
        ["Apenas Savings (Eficiência)", "Apenas Desvios (Gastos)", "Análise 360° (Ambos)"]
    )

    if st.sidebar.button("🔄 Resetar Navegação", use_container_width=True):
        st.session_state.drill_path = []
        st.rerun()

# --- 6. EXECUÇÃO DO DASHBOARD ---
st.title("📊 Auditoria Estratégica Facilities")
st.markdown("---")

if len(uploaded_files) >= 2:
    # Aplicação dos filtros globais da Sidebar
    df_filtrado = df_raw[df_raw['Mes'].isin(selecao_meses)]
    
    # Navegação por Clique (Drill-down)
    df_active = df_filtrado.copy()
    for col, val in st.session_state.drill_path:
        df_active = df_active[df_active[col] == val]

    # Localização Atual (Breadcrumbs)
    path_txt = " > ".join([str(v) for c, v in st.session_state.drill_path]) if st.session_state.drill_path else "Visão Geral"
    st.info(f"📍 **Escopo Atual:** `{path_txt}` | **Meses:** `{len(selecao_meses)} selecionados`")

    # Hierarquia de Visualização
    hierarquia = ['Localidade', 'Centro_Custo', 'Classe_Custo', 'Texto_Material']
    nivel = len(st.session_state.drill_path)

    if nivel < len(hierarquia):
        atual_col = hierarquia[nivel]
        
        # Visual 1: Gráfico YoY
        st.plotly_chart(plot_drilldown_chart(df_active, atual_col, ano_at, ano_ant), use_container_width=True)
        
        # Visual 2: Tabela Dinâmica
        st.markdown("---")
        c1, c2 = st.columns([3, 1])
        with c1: st.subheader(f"📂 Detalhamento por {atual_col}")
        with c2: 
            if nivel > 0 and st.button("⬅️ Voltar Nível", use_container_width=True):
                voltar_nivel(); st.rerun()

        df_pivot = render_dynamic_table(df_active, atual_col, ano_at, ano_ant)
        cols_meses = [c for c in df_pivot.columns if c != 'Total Geral']

        event = st.dataframe(
            df_pivot.style.format(precision=2, decimal=',', thousands='.').map(apply_color_logic, subset=cols_meses),
            use_container_width=True, 
            on_select="rerun", 
            selection_mode="single-row", 
            key=f"tab_audit_{nivel}"
        )

        # --- 7. MÓDULO DE IA: RELATÓRIO EXAUSTIVO SOB DEMANDA ---
        st.markdown("---")
        st.subheader("🕵️ Gerador de Auditoria IA (Exaustivo)")
        st.caption("A IA analisará todas as variações conforme os filtros selecionados na barra lateral.")

        if st.button("🚀 Gerar Auditoria Completa", use_container_width=True):
            if not dimensoes_ia:
                st.warning("⚠️ Selecione as dimensões na barra lateral (ex: Classe_Custo) para gerar o relatório.")
            else:
                with st.status("Llama 3.3 realizando auditoria profunda...", expanded=True):
                    # Agrupamento dinâmico conforme seleção do usuário na Sidebar
                    df_sumario_ia = df_filtrado.groupby(dimensoes_ia + ['Ano'])['Valor'].sum().unstack(level='Ano').fillna(0)
                    
                    # Garante que os anos de comparação existem
                    for a in [ano_at, ano_ant]:
                        if a not in df_sumario_ia.columns: df_sumario_ia[a] = 0
                    
                    df_sumario_ia['Variacao_Absoluta'] = df_sumario_ia[ano_at] - df_sumario_ia[ano_ant]
                    
                    # Filtro de Resultado (Savings vs Desvios)
                    if foco_resultado == "Apenas Savings (Eficiência)":
                        df_sumario_ia = df_sumario_ia[df_sumario_ia['Variacao_Absoluta'] < 0]
                    elif foco_resultado == "Apenas Desvios (Gastos)":
                        df_sumario_ia = df_sumario_ia[df_sumario_ia['Variacao_Absoluta'] > 0]
                    
                    # Preparação do Texto (Sem limites de linhas para auditoria completa)
                    base_string_ia = df_sumario_ia.sort_values(by='Variacao_Absoluta').to_string()
                    
                    contexto_audit = f"Filtros: {dimensoes_ia} | Escopo: {path_txt} | Foco: {foco_resultado}"
                    relatorio_final = get_ai_insights(base_string_ia, contexto_audit, api_key)
                    
                    st.markdown("---")
                    st.markdown(relatorio_final)

        # Captura de Clique para Navegação
        if event.selection.rows:
            st.session_state.drill_path.append((atual_col, df_pivot.index[event.selection.rows[0]]))
            st.rerun()
    else:
        st.success("🎯 Detalhe máximo atingido.")
        if st.button("⬅️ Voltar"): voltar_nivel(); st.rerun()
else:
    st.info("👋 Bem-vindo à Auditoria Facilities. Comece carregando os arquivos CSV na barra lateral.")