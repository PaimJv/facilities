import streamlit as st
import pandas as pd
from utils import clean_data, get_yoy_data

@st.cache_data(show_spinner=False)
def load_and_process_base(files, apenas_completos):
    try:
        dfs = [clean_data(pd.read_csv(f, sep=';', encoding='latin-1')) for f in files]
        full_df = pd.concat(dfs, ignore_index=True)
        return get_yoy_data(full_df, apenas_completos=apenas_completos)
    except Exception as e:
        return e, None, None

def init_state():
    if 'drill_path' not in st.session_state:
        st.session_state.drill_path = []

def voltar_nivel():
    if st.session_state.drill_path:
        st.session_state.drill_path.pop()

def apply_color_logic(val):
    if isinstance(val, (int, float)):
        if val < 0: return 'background-color: #D4EDDA; color: #155724'
        elif val > 0: return 'background-color: #F8D7DA; color: #721C24'
    return ''