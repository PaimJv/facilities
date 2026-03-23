import streamlit as st
import pandas as pd
from utils import clean_data, get_yoy_data
from ia_engine import get_ai_insights
from components import plot_yoy_chart, plot_drilldown_chart, render_dynamic_table

# 1. Configuração da Página
st.set_page_config(
    page_title="Facilities Analytics YoY",
    page_icon="📊",
    layout="wide"
)

# 2. Carregamento da API KEY
@st.cache_resource
def get_api_key():
    try:
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return None

api_key = get_api_key()
if not api_key:
    st.error("Erro: 'GROQ_API_KEY' não encontrada. Verifique o ficheiro .streamlit/secrets.toml")
    st.stop()

# 3. Processamento Cacheado (Alta Performance)
@st.cache_data(show_spinner=False)
def load_and_process_data(files, apenas_completos):
    try:
        dfs = [clean_data(pd.read_csv(f, sep=';', encoding='latin-1')) for f in files]
        full_df = pd.concat(dfs, ignore_index=True)
        return get_yoy_data(full_df, apenas_completos=apenas_completos)
    except Exception as e:
        return e, None, None

# 4. Gestão de Estado da Navegação
if 'drill_path' not in st.session_state:
    st.session_state.drill_path = []

def reset_nav():
    st.session_state.drill_path = []

def voltar_nivel():
    if st.session_state.drill_path:
        st.session_state.drill_path.pop()

# --- FUNÇÃO DE CORES SIMPLES (VERDE/VERMELHO) ---
def apply_color_logic(val):
    """Lógica direta: Negativo é bom (Verde), Positivo é ruim (Vermelho)."""
    if isinstance(val, (int, float)):
        if val < 0:
            return 'background-color: #D4EDDA; color: #155724' # Verde claro com texto escuro
        elif val > 0:
            return 'background-color: #F8D7DA; color: #721C24' # Vermelho claro com texto escuro
    return ''

# --- BARRA LATERAL ---
st.sidebar.title("⚙️ Filtros de Análise")
modo_periodo = st.sidebar.radio(
    "Considerar meses:",
    ["Meses Completos (Fechados)", "Incluir Mês Atual (Incompleto)"],
    index=1
)
apenas_completos = (modo_periodo == "Meses Completos (Fechados)")

if st.sidebar.button("🔄 Resetar Navegação (Topo)", use_container_width=True):
    reset_nav()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.write("✅ **Legenda:**")
st.sidebar.write("🟢 **Verde:** Redução (Saving)")
st.sidebar.write("🔴 **Vermelho:** Aumento (Gasto)")

st.title("📊 Dashboard de Produtividade Facilities")
st.markdown("---")

uploaded_files = st.file_uploader(
    "Upload dos ficheiros CSV (ex: 2025 e 2026):", 
    accept_multiple_files=True,
    type=["csv"]
)

# 5. Execução
if len(uploaded_files) >= 2:
    data_result = load_and_process_data(uploaded_files, apenas_completos)
    
    if isinstance(data_result[0], Exception):
        st.error(f"Erro no processamento: {data_result[0]}")
        st.stop()
    
    df_comp, ano_atual, ano_anterior = data_result

    if not df_comp.empty:
        # Filtro de navegação
        df_active = df_comp.copy()
        for col, val in st.session_state.drill_path:
            if col in df_active.columns:
                df_active = df_active[df_active[col] == val]

        # Breadcrumbs
        path_str = " > ".join([str(v) for c, v in st.session_state.drill_path]) if st.session_state.drill_path else "Visão Geral"
        st.markdown(f"**📍 Localização:** `Início > {path_str}`")

        # Hierarquia
        hierarquia = ['Localidade', 'Centro_Custo', 'Classe_Custo', 'Texto_Material']
        nivel = len(st.session_state.drill_path)

        if nivel < len(hierarquia):
            atual_col = hierarquia[nivel]
            labels = {'Localidade': 'Localidade', 'Centro_Custo': 'Centro de Custo', 
                     'Classe_Custo': 'Classe de Custo (Contas)', 'Texto_Material': 'Material'}
            label_atual = labels.get(atual_col, atual_col)

            # Gráfico
            st.plotly_chart(plot_drilldown_chart(df_active, atual_col, ano_atual, ano_anterior), use_container_width=True)
            
            # Tabela Dinâmica
            st.markdown("---")
            col_tit, col_btn = st.columns([3, 1])
            with col_tit:
                st.subheader(f"📂 Visão Detalhada Mensal: {label_atual}")
            with col_btn:
                if nivel > 0:
                    st.write("##") 
                    if st.button("⬅️ Voltar Nível", use_container_width=True, key="btn_back"):
                        voltar_nivel(); st.rerun()

            try:
                df_pivot = render_dynamic_table(df_active, atual_col, ano_atual, ano_anterior)
                
                # Identifica colunas de meses (ignora Total Geral na pintura se preferir)
                cols_to_style = [c for c in df_pivot.columns if c != 'Total Geral']

                # Renderiza com a lógica de mapa de cores (CSS direto)
                event = st.dataframe(
                    df_pivot.style.format(precision=2, decimal=',', thousands='.')
                    .map(apply_color_logic, subset=cols_to_style), # AQUI ESTÁ A MUDANÇA
                    use_container_width=True,
                    on_select="rerun",
                    selection_mode="single-row",
                    key=f"pivot_table_{nivel}"
                )

                if event.selection.rows:
                    row_idx = event.selection.rows[0]
                    selecao_nome = df_pivot.index[row_idx]
                    st.session_state.drill_path.append((atual_col, selecao_nome))
                    st.rerun()

            except Exception as e:
                st.warning(f"Erro na renderização: {e}")

        else:
            st.success("🎯 Nível máximo atingido.")
            if st.button("⬅️ Voltar"): voltar_nivel(); st.rerun()

        # IA Insights
        st.markdown("---")
        if st.button("🚀 Gerar Insights com IA"):
            with st.spinner("Analisando..."):
                mat_pivot = df_active.groupby(['Ano', 'Texto_Material'])['Valor'].sum().unstack(level=0).fillna(0)
                if ano_anterior in mat_pivot.columns:
                    mat_pivot['Var'] = mat_pivot[ano_atual] - mat_pivot[ano_anterior]
                    resumo_ia = mat_pivot.sort_values(by='Var').head(15).to_string()
                    insights = get_ai_insights(resumo_ia, f"Filtros: {st.session_state.drill_path}", api_key)
                    st.info("📝 Relatório da IA:")
                    st.markdown(insights)
else:
    st.info("Aguardando o upload de pelo menos 2 ficheiros CSV.")