import streamlit as st
from logic import init_state, load_and_process_base, voltar_nivel, apply_color_logic
from sidebar import render_initial_sidebar, render_advanced_filters
from ia_engine import get_ai_insights
from components import plot_drilldown_chart, render_dynamic_table

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Auditoria Estratégica Facilities",
    page_icon="🕵️‍♂️",
    layout="wide"
)

# Inicializa o estado da sessão (drill_path)
init_state()

# Recupera a chave de API dos secrets
api_key = st.secrets.get("GROQ_API_KEY", None)

# --- 2. INTERFACE INICIAL ---
st.title("📊 Auditoria de Produtividade YoY")
st.caption("Análise de Variação de Custos com Auditoria Exaustiva por IA")
st.markdown("---")

# Renderiza a primeira parte da sidebar (Modo e Upload)
apenas_completos, uploaded_files = render_initial_sidebar()

if len(uploaded_files) >= 2:
    # --- 3. PROCESSAMENTO DE DADOS ---
    # df_raw já vem com a coluna 'Desc_Conta' formatada ("Descrição - Código")
    df_raw, ano_at, ano_ant = load_and_process_base(uploaded_files, apenas_completos)
    
    if isinstance(df_raw, str):
        st.error(f"Erro no processamento: {df_raw}")
        st.stop()

    # --- 4. FILTROS AVANÇADOS (SIDEBAR ETAPA 2) ---
    # Só renderiza após o df_raw estar pronto
    selecao_meses, dimensoes_ia, foco_res, filtros_dinamicos = render_advanced_filters(df_raw)

    # --- 5. LÓGICA DE FILTRAGEM E DRILL-DOWN ---
    # A. Filtro de Meses
    meses_filtro = selecao_meses if selecao_meses else sorted(df_raw['Mes'].unique())
    df_filtrado = df_raw[df_raw['Mes'].isin(meses_filtro)]
    
    # B. Filtros Inteligentes (Cross-filtering da Sidebar)
    # Aqui é onde a mágica acontece: se você filtrar uma Localidade, 
    # o df_filtrado diminui e tudo que vem abaixo dele (Gráfico/Tabela) obedece.
    if filtros_dinamicos:
        for col, valores in filtros_dinamicos.items():
            if valores:
                # Garantimos que a comparação seja feita como string para evitar erros de tipo
                df_filtrado = df_filtrado[df_filtrado[col].astype(str).isin(valores)]
    
    # C. Lógica de Drill-down (Navegação por clique)
    # df_active é o que os gráficos e tabelas realmente usam
    df_active = df_filtrado.copy()
    for col, val in st.session_state.drill_path:
        if col in df_active.columns:
            df_active = df_active[df_active[col].astype(str) == str(val)]

    # Breadcrumbs (Navegação Visual)
    path_txt = " > ".join([str(v) for c, v in st.session_state.drill_path]) if st.session_state.drill_path else "Corporativo"
    st.info(f"📍 **Localização:** `Início > {path_txt}`")

    # --- 6. HIERARQUIA DE NAVEGAÇÃO ---
    hierarquia = ['Desc_Conta', 'P_L', 'VP', 'Localidade', 'Centro_Custo', 'Desc_Material']
    labels = {
        'Desc_Conta': 'Conta (Classe de Custo)', 
        'P_L': 'P&L', 
        'VP': 'VP', 
        'Localidade': 'Localidade', 
        'Centro_Custo': 'Centro de Custo', 
        'Desc_Material': 'Material'
    }
    
    nivel = len(st.session_state.drill_path)

    if nivel < len(hierarquia):
        atual_col = hierarquia[nivel]
        label_atual = labels.get(atual_col, atual_col)

        # Gráfico de Impacto
        st.plotly_chart(plot_drilldown_chart(df_active, atual_col, ano_at, ano_ant), use_container_width=True)
        
        # Cabeçalho da Tabela e Botão Voltar
        st.markdown("---")
        c1, c2 = st.columns([4, 1])
        with c1:
            st.subheader(f"📂 Visão Mensal: {label_atual}")
        with c2:
            if nivel > 0:
                st.write("##")
                if st.button("⬅️ Voltar Nível", use_container_width=True, key="btn_back_main"):
                    voltar_nivel()
                    st.rerun()

        # Matriz de Variação
        df_pivot = render_dynamic_table(df_active, atual_col, ano_at, ano_ant)
        cols_meses = [c for c in df_pivot.columns if c != 'Total Geral']

        # Exibição da Tabela com Seleção de Linha
        event = st.dataframe(
            df_pivot.style.format(precision=2, decimal=',', thousands='.')
            .map(apply_color_logic, subset=cols_meses),
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
            key=f"tab_drill_{nivel}"
        )

        # --- 7. RELATÓRIO DE AUDITORIA IA ---
        st.markdown("---")
        st.subheader("🕵️ Auditoria Estratégica IA")
        
        if st.button("🚀 Gerar Auditoria Exaustiva", use_container_width=True, key="btn_ia_run"):
            if not dimensoes_ia:
                st.warning("⚠️ Selecione as dimensões na barra lateral para análise.")
            else:
                with st.status("IA analisando desvios e causas raízes...", expanded=True):
                    # Agrupamento dinâmico conforme sidebar
                    df_sum_ia = df_filtrado.groupby(dimensoes_ia + ['Ano'])['Valor'].sum().unstack(level='Ano').fillna(0)
                    
                    # Verificação de colunas de ano
                    for a in [ano_at, ano_ant]:
                        if a not in df_sum_ia.columns: df_sum_ia[a] = 0
                    
                    df_sum_ia['Variacao'] = df_sum_ia[ano_at] - df_sum_ia[ano_ant]
                    
                    # Filtro de foco (Savings vs Desvios)
                    if "Savings" in foco_res:
                        df_sum_ia = df_sum_ia[df_sum_ia['Variacao'] < 0]
                    elif "Desvios" in foco_res:
                        df_sum_ia = df_sum_ia[df_sum_ia['Variacao'] > 0]
                    
                    # Envio exaustivo (sem .head())
                    resumo_ia = df_sum_ia.sort_values(by='Variacao').to_string()
                    contexto = f"Hierarquia: {dimensoes_ia} | Localização: {path_txt} | Foco: {foco_res}"
                    
                    relatorio = get_ai_insights(resumo_ia, contexto, api_key)
                    st.markdown(relatorio)

        # Captura de clique na tabela para descer de nível
        if event.selection.rows:
            selecao = df_pivot.index[event.selection.rows[0]]
            st.session_state.drill_path.append((atual_col, selecao))
            st.rerun()

    else:
        # Nível Final (Material)
        st.success("🎯 Detalhe máximo atingido (Análise por Material).")
        if st.button("⬅️ Voltar ao Início", use_container_width=True):
            st.session_state.drill_path = []
            st.rerun()
else:
    st.info("👋 Para começar, carregue os arquivos CSV de dois anos diferentes na barra lateral.")