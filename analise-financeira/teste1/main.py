import streamlit as st
import pandas as pd
from engine import FinanceEngine
from interface_assets import ST_STYLE

st.set_page_config(page_title="Financial AI Master", layout="wide")
eng = FinanceEngine()

def format_br(val, is_perc=False):
    if is_perc: return f"{val:+.1f}%".replace('.', ',')
    return f"R$ {val:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')

st.title("📂 Financial AI Pivot: Analisador de Performance")

with st.sidebar:
    f24 = st.file_uploader("Base 2024", type="csv", key="u24")
    f25 = st.file_uploader("Base 2025", type="csv", key="u25")

if f24 and f25:
    d24, m24 = eng.clean_file(f24)
    d25, m25 = eng.clean_file(f25)
    max_m = d25['Mes'].max()
    d24 = d24[d24['Mes'] <= max_m]
    m_idx, m_names = list(range(1, max_m + 1)), ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"][:max_m]

    idx = ['CC', 'Classe']
    p24 = d24.pivot_table(index=idx, columns='Mes', values=m24['valor'], aggfunc='sum').fillna(0)
    p25 = d25.pivot_table(index=idx, columns='Mes', values=m25['valor'], aggfunc='sum').fillna(0)
    all_idx = p24.index.union(p25.index)
    p24, p25 = p24.reindex(all_idx, fill_value=0), p25.reindex(all_idx, fill_value=0)
    delta = p25 - p24
    
    centros_lista = sorted(all_idx.get_level_values(0).unique())
    # Construção estática do menu de filtro
    cc_options_html = "".join([f'<div class="filter-menu-item"><input type="checkbox" value="{cc}" checked> {cc}</div>' for cc in centros_lista])

    table_html = f'<table class="pivot-table"><thead><tr>'
    table_html += f'<th class="label-col" onclick="sortTable(0)">Hierarquia (CC > Classe) <span class="sort-icon">↕</span> <span class="filter-trigger" onclick="toggleFilterMenu(event)">▼</span></th>'
    for i, n in enumerate(m_names):
        table_html += f'<th onclick="sortTable({i+1})">{n} <span class="sort-icon">↕</span></th>'
    table_html += f'<th class="total-col-head" style="border-left: 2px solid #ddd;" onclick="sortTable({len(m_names)+1})">TOTAL (YTD) <span class="sort-icon">↕</span></th></tr></thead><tbody>'

    for i, cc in enumerate(centros_lista):
        cc_d_m, cc_p24_m = delta.loc[cc].sum(), p24.loc[cc].sum()
        cc_ytd_d = cc_d_m.sum()
        cc_ytd_p = (cc_ytd_d / cc_p24_m.sum() * 100) if cc_p24_m.sum() != 0 else 0
        cc_id = f"cc_{i}"
        
        table_html += f'<tr class="cc-row" data-cc-name="{cc}" onclick="toggleGroup(\'{cc_id}\')"><td class="label-col"><span id="icon-{cc_id}" class="exp-icon">[+]</span>{cc}</td>'
        for m in m_idx:
            v, p = cc_d_m[m], (cc_d_m[m]/cc_p24_m[m]*100 if cc_p24_m[m] != 0 else 0)
            sub_m_data = delta.loc[cc, m].sort_values()
            top_pts = [(cl, val) for cl, val in sub_m_data.items() if val != 0]
            table_html += f'<td><div class="tooltip {"val-pos" if v > 0 else "val-neg"}">{format_br(v)}<br>({format_br(p, True)})<span class="tt-text">{eng.get_ai_insight(v, p, cc, top_pts)}</span></div></td>'
        table_html += f'<td class="total-cell"><div class="tooltip {"val-pos" if cc_ytd_d > 0 else "val-neg"}">{format_br(cc_ytd_d)}<br>({format_br(cc_ytd_p, True)})<span class="tt-text">{eng.get_ai_insight(cc_ytd_d, cc_ytd_p, cc)}</span></div></td></tr>'

        classes = all_idx[all_idx.get_level_values(0) == cc].get_level_values(1).unique()
        for cl in classes:
            cl_d, cl_24, cl_25 = delta.loc[(cc,cl)], p24.loc[(cc,cl)], p25.loc[(cc,cl)]
            cl_ytd_d, cl_ytd_p = (cl_25.sum() - cl_24.sum()), 0
            if cl_24.sum() != 0: cl_ytd_p = (cl_ytd_d / cl_24.sum() * 100)
            
            table_html += f'<tr class="class-row child-{cc_id}"><td class="label-col" style="padding-left: 45px !important;">↳ {cl}</td>'
            for m in m_idx:
                v, p = cl_d[m], (cl_d[m]/cl_24[m]*100 if cl_24[m] != 0 else 0)
                table_html += f'<td><div class="tooltip {"val-pos" if v > 0 else "val-neg"}">{format_br(v)}<br>({format_br(p, True)})<span class="tt-text">{eng.get_ai_insight(v, p, cl)}</span></div></td>'
            table_html += f'<td class="total-cell"><div class="tooltip {"val-pos" if cl_ytd_d > 0 else "val-neg"}">{format_br(cl_ytd_d)}<br>({cl_ytd_p:+.1f}%)<span class="tt-text">Performance anual da Conta.</span></div></td></tr>'

    table_html += '</tbody></table>'
    
    # Injeção unificada e segura
    full_html = f"""
    {ST_STYLE}
    <div id="ccFilterMenu" class="filter-menu">
        <div id="ccList">{cc_options_html}</div>
        <div class="filter-actions">
            <button class="btn-filter" onclick="document.querySelectorAll('#ccList input').forEach(cb => cb.checked = true)">Todos</button>
            <button class="btn-filter" onclick="document.querySelectorAll('#ccList input').forEach(cb => cb.checked = false)">Nenhum</button>
            <button class="btn-filter btn-apply" onclick="applyCCFilter()">Aplicar</button>
        </div>
    </div>
    <div class='pivot-container'>{table_html}</div>
    """
    st.components.v1.html(full_html, height=1200, scrolling=True)
else:
    st.info("💡 Carregue os arquivos para gerar a Tabela Dinâmica Inteligente.")