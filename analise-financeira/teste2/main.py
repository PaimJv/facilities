import streamlit as st
from logic import load_and_process_base, init_state, voltar_nivel, apply_color_logic
from sidebar import render_sidebar
from ia_engine import get_ai_insights
from components import plot_drilldown_chart, render_dynamic_table

# Configuração e Estado
st.set_page_config(page_title="Auditoria Avançada Facilities", page_icon="🕵️‍♂️", layout="wide")
init_state()

# API Key
@st.cache_resource
def get_api_key():
    return st.secrets.get("GROQ_API_KEY", "")

api_key = get_api_key()

# Título e Upload
st.title("📊 Auditoria Estratégica Facilities")
uploaded_files = st.file_uploader("Carregue os ficheiros CSV:", accept_multiple_files=True, type=["csv"])

if len(uploaded_files) >= 2:
    # Processamento e Sidebar
    df_raw, ano_at, ano_ant = load_and_process_base(uploaded_files, False)
    selecao_meses, dimensoes_ia, foco_resultado = render_sidebar(df_raw)

    # Aplicação de Filtros
    df_filtrado = df_raw[df_raw['Mes'].isin(selecao_meses)]
    df_active = df_filtrado.copy()
    for col, val in st.session_state.drill_path:
        df_active = df_active[df_active[col] == val]

    # Breadcrumbs
    path_txt = " > ".join([str(v) for c, v in st.session_state.drill_path]) if st.session_state.drill_path else "Geral"
    st.info(f"📍 **Escopo:** `{path_txt}`")

    # Navegação Hierárquica
    hierarquia = ['Localidade', 'Centro_Custo', 'Classe_Custo', 'Texto_Material']
    nivel = len(st.session_state.drill_path)

    if nivel < len(hierarquia):
        atual_col = hierarquia[nivel]
        st.plotly_chart(plot_drilldown_chart(df_active, atual_col, ano_at, ano_ant), use_container_width=True)
        
        st.markdown("---")
        c1, c2 = st.columns([3, 1])
        with c1: st.subheader(f"📂 Detalhe: {atual_col}")
        with c2: 
            if nivel > 0 and st.button("⬅️ Voltar"): voltar_nivel(); st.rerun()

        df_pivot = render_dynamic_table(df_active, atual_col, ano_at, ano_ant)
        cols_meses = [c for c in df_pivot.columns if c != 'Total Geral']

        event = st.dataframe(
            df_pivot.style.format(precision=2, decimal=',', thousands='.').map(apply_color_logic, subset=cols_meses),
            use_container_width=True, on_select="rerun", selection_mode="single-row", key=f"tab_{nivel}"
        )

        # --- RELATÓRIO IA ---
        st.markdown("---")
        if st.button("🚀 Gerar Auditoria Completa", use_container_width=True):
            with st.status("IA processando...", expanded=True):
                df_sumario_ia = df_filtrado.groupby(dimensoes_ia + ['Ano'])['Valor'].sum().unstack(level='Ano').fillna(0)
                df_sumario_ia['Variacao'] = df_sumario_ia[ano_at] - df_sumario_ia[ano_ant]
                
                if foco_resultado == "Apenas Savings (Eficiência)":
                    df_sumario_ia = df_sumario_ia[df_sumario_ia['Variacao'] < 0]
                elif foco_resultado == "Apenas Desvios (Gastos)":
                    df_sumario_ia = df_sumario_ia[df_sumario_ia['Variacao'] > 0]
                
                resumo_txt = df_sumario_ia.sort_values(by='Variacao').to_string()
                relatorio = get_ai_insights(resumo_txt, f"Filtros: {dimensoes_ia} | Escopo: {path_txt}", api_key)
                st.markdown(relatorio)

        if event.selection.rows:
            st.session_state.drill_path.append((atual_col, df_pivot.index[event.selection.rows[0]]))
            st.rerun()
    else:
        st.success("🎯 Detalhe máximo atingido.")
        if st.button("⬅️ Voltar"): voltar_nivel(); st.rerun()
else:
    st.info("👋 Aguardando CSVs para auditoria.")