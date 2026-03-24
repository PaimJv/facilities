import pandas as pd
import numpy as np
import unicodedata

class FinanceEngine:
    def __init__(self):
        self.keys = {
            'data': ['data', 'lanca'],
            'cc_id': ['centro', 'custo'],
            'cc_nome': ['denomina', 'objeto'],
            'classe_id': ['classe', 'custo'],
            'classe_nome': ['denom', 'classe', 'custo'],
            'valor': ['valor', 'moeda', 'objeto']
        }

    def normalize(self, text):
        return "".join([c for c in unicodedata.normalize('NFKD', str(text)) if not unicodedata.combining(c)]).lower().strip()

    def map_cols(self, df):
        headers = [h.replace('\ufeff', '').strip() for h in df.columns]
        df.columns = headers
        mapping = {}
        for k, words in self.keys.items():
            for h in headers:
                if all(self.normalize(w) in self.normalize(h) for w in words):
                    mapping[k] = h
                    break
        return mapping

    def clean_file(self, file):
        df = pd.read_csv(file, sep=';', encoding='utf-8-sig')
        m = self.map_cols(df)
        v = m['valor']
        if df[v].dtype == object:
            df[v] = df[v].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df[v] = pd.to_numeric(df[v], errors='coerce').fillna(0)
        df['Data_Ref'] = pd.to_datetime(df[m['data']], dayfirst=True)
        df['Mes'] = df['Data_Ref'].dt.month
        df['CC'] = df[m['cc_id']].astype(str) + " - " + df[m['cc_nome']].astype(str)
        df['Classe'] = df[m['classe_id']].astype(str) + " - " + df[m['classe_nome']].astype(str)
        return df, m

    def format_br(self, val, is_perc=False):
        """Helper para formatar números no padrão PT-BR"""
        if is_perc:
            return f"{val:+.1f}%".replace('.', ',')
        # Formata com milhar em , e decimal em . depois inverte
        return f"R$ {val:,.2f}".replace(',', 'v').replace('.', ',').replace('v', '.')

    def get_ai_insight(self, diff, p, label, sub_points=None):
        status = "Prejuízo" if diff > 0 else "Lucro"
        header = f"<span class='insight-title'>🧠 IA FINANCIAL INSIGHT</span>"
        
        # Uso da formatação BR aqui
        diff_form = self.format_br(diff)
        perc_form = self.format_br(p, is_perc=True)
        
        base_text = f"Análise de <b>{label}</b>:<br>Variação de {perc_form} ({diff_form}) caracterizada como {status}."
        
        points_html = ""
        if sub_points:
            profits = [f"{c[:30]} ({self.format_br(v)})" for c, v in sub_points if v < 0]
            losses = [f"{c[:30]} (+{self.format_br(v)})" for c, v in sub_points if v > 0]
            if profits: points_html += f"<br><br><span class='point-profit'>▲ Contas com Lucro:</span><br>• " + "<br>• ".join(profits[:2])
            if losses: points_html += f"<br><br><span class='point-loss'>▼ Contas com Prejuízo:</span><br>• " + "<br>• ".join(losses[:2])
        
        return f"{header}{base_text}{points_html}"