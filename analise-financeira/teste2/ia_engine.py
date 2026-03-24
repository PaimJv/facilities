import streamlit as st
from groq import Groq

@st.cache_data(show_spinner=False)
def get_ai_insights(data_summary, context_text, api_key):
    """
    Motor de Auditoria Estratégica Multi-nível.
    Realiza uma análise exaustiva de variação (Variance Analysis) baseada 
    nos filtros customizados aplicados pelo utilizador.
    """
    
    if not api_key:
        return "⚠️ Erro: Chave de API da Groq não configurada. Verifique o secrets.toml."

    try:
        # 1. Inicialização do Cliente
        client = Groq(api_key=api_key)

        # 2. Definição da Persona: Auditor Sênior de Controladoria e Engenharia
        # Foco em Causa Raiz, Sustentabilidade Financeira e Eficiência Operacional.
        system_instruction = (
            "Você é um Auditor Sênior de Controladoria e Engenheiro de Dados de Facilities. "
            "Sua especialidade é Auditoria de Desvios (Variance Audit). "
            "Sua análise deve ser técnica, profunda e executiva. "
            "Terminologia: 'Classe de Custo' refere-se às Contas Contábeis; 'Saving' é redução de custo."
        )

        # 3. Engenharia de Prompt para Auditoria Sem Limites
        user_prompt = f"""
        REALIZE UMA AUDITORIA EXAUSTIVA DE DESEMPENHO FINANCEIRO YOY. 
        Não limite sua análise; aborde todos os detalhes relevantes contidos na base fornecida.

        ### ESCOPO DA AUDITORIA (FILTROS E CONTEXTO):
        {context_text}

        ### BASE DE DADOS COMPLETA (VARIAÇÃO POR DIMENSÃO):
        {data_summary}

        ---
        ### REQUISITOS DO RELATÓRIO (ESTRUTURA EM MARKDOWN):

        1. **DIAGNÓSTICO POR CATEGORIA:** Analise as variações cruzando as dimensões selecionadas (Localidade vs Centro de Custo vs Classe de Custo). 
           Identifique onde está a maior concentração de economia ou desvio.

        2. **ANÁLISE DE CAUSA RAIZ E EFICIÊNCIA:**
           Para os resultados de Savings (Redução), determine o padrão:
           - **Eficiência Estrutural:** Mudança em contratos ou processos.
           - **Otimização de Demanda:** Redução real de consumo/uso.
           - **Variação de Escala:** Ganhos por volume ou centralização.

        3. **MATRIZ DE RISCO E SUSTENTABILIDADE:**
           Diferencie o que é um ganho sustentável (que se manterá no próximo ano) do que é uma oscilação pontual (ex: atraso de pagamento, sazonalidade extrema).

        4. **PLANO DE REPLICABILIDADE TÉCNICA:**
           Crie um checklist de ações de Engenharia de Facilities e Gestão de Contratos para replicar os bons resultados em áreas críticas.

        5. **CONCLUSÃO EXECUTIVA:**
           Dê um veredito sobre a saúde financeira do escopo analisado.

        ---
        **Instruções de Estilo:** Use tabelas Markdown para comparar ofensores vs cases de sucesso. Use **negrito** para destacar valores monetários e KPIs.
        """

        # 4. Chamada ao Modelo (Llama 3.3 70b)
        # Temperatura 0.1: Rigor matemático e técnico.
        # Max_tokens 4000: Permite uma análise exaustiva sem cortes no texto.
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=4000,
            top_p=1,
            stream=False,
        )

        return completion.choices[0].message.content

    except Exception as e:
        return f"❌ Erro crítico na geração da auditoria: {str(e)}"