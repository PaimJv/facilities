import pandas as pd
from datetime import datetime, timedelta
import os
import warnings

# Silencia avisos de formatação do Excel
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# --- FUNÇÕES DE APOIO ---

def calcular_duracao(inicio, fim):
    """Calcula a diferença entre dois horários HH:MM, tratando virada de dia."""
    try:
        fmt = "%H:%M"
        t1_str = str(inicio).strip()[:5]
        t2_str = str(fim).strip()[:5]
        t1 = datetime.strptime(t1_str, fmt)
        t2 = datetime.strptime(t2_str, fmt)
        if t2 < t1: t2 += timedelta(days=1)
        diff = t2 - t1
        horas, segundos = divmod(diff.seconds, 3600)
        minutos = (diff.seconds // 60) % 60
        return f"{horas:02d}:{minutos:02d}"
    except:
        return "00:00"

def e_numero(valor):
    """Verifica se o valor na Coluna D (índice 3) é um número."""
    if pd.isna(valor): return False
    try:
        float(str(valor).replace(',', '.'))
        return True
    except:
        return False

def buscar_horario_acima(df, linha_inicio):
    """Busca o primeiro horário válido subindo as linhas na Coluna E (índice 4)."""
    for i in range(linha_inicio - 1, -1, -1):
        valor = df.iloc[i, 4]
        if pd.notna(valor):
            valor_str = str(valor).strip()
            # Verifica se tem formato de hora (ex: 12:50)
            if ":" in valor_str and len(valor_str) >= 4:
                return valor_str[:5]
    return "00:00"

def processar_logistica_pepsico(arquivo_excel, arquivo_setores_csv, arquivo_base_geral=None):
    # 1. CARREGAR REFERÊNCIA DE SETORES (UTF-8)
    try:
        df_setores_ref = pd.read_csv(arquivo_setores_csv, sep=None, engine='python', encoding='utf-8-sig', header=None)
        lista_setores = df_setores_ref[2].dropna().astype(str).str.strip().str.upper().unique().tolist()
        print(f"✅ {len(lista_setores)} setores carregados da base de referência.")
    except Exception as e:
        print(f"❌ Erro ao ler CSV de setores: {e}")
        return

    # 2. CARREGAR BASE GERAL
    base_geral_nomes = []
    if arquivo_base_geral and os.path.exists(arquivo_base_geral):
        try:
            df_g = pd.read_excel(arquivo_base_geral)
            base_geral_nomes = df_g.iloc[:, 0].astype(str).str.strip().str.upper().unique().tolist()
        except:
            print("⚠️ Base geral não carregada.")

    # 3. ANALISAR EXCEL DE ROTAS
    print(f"🔍 Analisando todas as abas de: {arquivo_excel}...")
    try:
        abas = pd.read_excel(arquivo_excel, sheet_name=None, header=None)
    except Exception as e:
        print(f"❌ Erro ao abrir o Excel: {e}")
        return

    relatorio_detalhado = []
    relatorio_resumido = []

    for nome_aba, df in abas.items():
        rota_atual = "N/A"
        temp_passageiros = []
        dentro_do_bloco = False

        for idx, row in df.iterrows():
            conteudo_linha = " ".join([str(item).upper() for item in row.values])
            
            # REGRA: Localizar Rota (2 linhas acima de PONTOS DE REFERÊNCIA)
            if "PONTOS DE REFERÊNCIA" in conteudo_linha or "PONTOS DE REFERENCIA" in conteudo_linha:
                dentro_do_bloco = True
                if idx >= 2:
                    valor_rota = df.iloc[idx - 2, 5] 
                    rota_atual = str(valor_rota).strip() if pd.notna(valor_rota) else "N/A"
                continue

            if "CHEGADA NA FÁBRICA PEPSICO" in conteudo_linha or "CHEGADA NA FABRICA" in conteudo_linha:
                dentro_do_bloco = False
                continue

            if dentro_do_bloco:
                setor_lido = str(row[1]).strip().upper() if pd.notna(row[1]) else ""
                identificado_por_setor = setor_lido in lista_setores
                identificado_por_numero = e_numero(row[3]) # Coluna D

                if identificado_por_setor or identificado_por_numero:
                    nome_func = str(row[2]).strip().upper() if pd.notna(row[2]) else ""
                    if nome_func and "HORÁRIO" not in nome_func and "HORARIO" not in nome_func:
                        
                        # Captura o horário individual (subindo na Coluna E)
                        h_individual = buscar_horario_acima(df, idx)
                        
                        # NOVA REGRA: Captura texto de Observação na Coluna E da própria linha
                        obs = str(row[4]).strip() if pd.notna(row[4]) else ""
                        # Se o que foi capturado for o próprio horário (caso raro de duplicidade), limpamos
                        if ":" in obs and len(obs) <= 5: obs = ""

                        temp_passageiros.append({
                            "aba": nome_aba,
                            "setor": setor_lido,
                            "nome": nome_func,
                            "rota": rota_atual,
                            "linha_idx": idx,
                            "hora_individual": h_individual,
                            "observacao": obs
                        })

        if temp_passageiros:
            df_aba_temp = pd.DataFrame(temp_passageiros)
            for r in df_aba_temp['rota'].unique():
                grupo = df_aba_temp[df_aba_temp['rota'] == r]
                idx_ini, idx_fim = grupo['linha_idx'].min(), grupo['linha_idx'].max()

                # Horários globais para o resumo
                h_partida_rota = buscar_horario_acima(df, idx_ini)
                h_chegada_fab = df.iloc[idx_fim + 1, 4] if idx_fim < len(df)-1 else "00:00"
                h_chegada_fab = str(h_chegada_fab).strip()[:5] if pd.notna(h_chegada_fab) else "00:00"
                duracao_rota = calcular_duracao(h_partida_rota, h_chegada_fab)

                for _, p in grupo.iterrows():
                    na_base = "SIM" if p['nome'] in base_geral_nomes else "NÃO"
                    relatorio_detalhado.append({
                        "ABA ORIGEM": p['aba'],
                        "SETOR/EMPRESA": p['setor'],
                        "NOME FUNCIONÁRIO": p['nome'],
                        "ROTA": p['rota'],
                        "HORÁRIO EMBARQUE": p['hora_individual'],
                        "CHEGADA FÁBRICA": h_chegada_fab,
                        "OBSERVAÇÃO": p['observacao'], # Nova coluna no detalhado
                        "NA BASE GERAL?": na_base if base_geral_nomes else "NÃO TESTADO"
                    })
                
                relatorio_resumido.append({
                    "ABA ORIGEM": nome_aba,
                    "ROTA": r,
                    "QTD FUNCIONÁRIOS": len(grupo),
                    "INÍCIO DA ROTA": h_partida_rota,
                    "CHEGADA FÁBRICA": h_chegada_fab,
                    "TEMPO TOTAL ROTA": duracao_rota
                })

    # 4. EXPORTAÇÃO
    if relatorio_detalhado:
        df_detalhe = pd.DataFrame(relatorio_detalhado)
        df_resumo = pd.DataFrame(relatorio_resumido)
        nome_arquivo = f"RELATORIO_FINAL_LOGISTICA_{datetime.now().strftime('%d_%m_%H%M')}.xlsx"
        with pd.ExcelWriter(nome_arquivo, engine='openpyxl') as writer:
            df_detalhe.to_excel(writer, sheet_name="DETALHADO", index=False)
            df_resumo.to_excel(writer, sheet_name="RESUMO_ROTAS", index=False)
        print(f"\n🚀 Sucesso! Relatório gerado com observações em: {nome_arquivo}")
    else:
        print("\n⚠️ Nenhum dado processado.")

if __name__ == "__main__":
    # Certifique-se de que os nomes dos arquivos abaixo estão corretos na sua pasta
    ARQUIVO_ROTAS = "facilities/fretado/07. ROTAS PEPSICO - A PARTIR DO DIA 05.03.2026.xlsx"
    SETOR_CSV = "facilities/fretado/Fretado Fab BA 2026(SETORES E EMPRESAS).csv"
    BASE_GERAL = "facilities/fretado/Fretado Fab BA 2026.xlsx"
    processar_logistica_pepsico(ARQUIVO_ROTAS, SETOR_CSV, BASE_GERAL)