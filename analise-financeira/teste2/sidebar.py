import streamlit as st

def render_sidebar(df_raw):
    st.sidebar.title("🔍 Parâmetros da Auditoria")
    st.sidebar.markdown("---")

    # Filtro de Meses
    meses_lista = sorted(df_raw['Mes'].unique())
    meses_br = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun',
                7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}
    
    selecao_meses = st.sidebar.multiselect(
        "2. Período (Meses):", 
        options=meses_lista, 
        default=meses_lista,
        format_func=lambda x: meses_br.get(x, x)
    )

    # Filtro de Dimensões para IA
    dimensoes_ia = st.sidebar.multiselect(
        "3. Dimensões para a IA:",
        ['Classe_Custo', 'Centro_Custo', 'Localidade', 'Diretoria', 'VP'],
        default=['Localidade', 'Classe_Custo']
    )

    # Filtro de Foco
    foco_resultado = st.sidebar.radio(
        "4. Foco da Análise:",
        ["Apenas Savings (Eficiência)", "Apenas Desvios (Gastos)", "Análise 360° (Ambos)"]
    )

    if st.sidebar.button("🔄 Resetar Navegação", use_container_width=True):
        st.session_state.drill_path = []
        st.rerun()

    return selecao_meses, dimensoes_ia, foco_resultado