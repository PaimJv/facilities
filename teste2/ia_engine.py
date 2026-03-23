from groq import Groq

def get_ai_insights(data_summary, context_text, api_key):
    """
    Interpreta os desvios financeiros e gera um relatório executivo.
    Foca em identificar 'ofensores' de custo e oportunidades de produtividade.
    """
    
    # 1. Validação da Chave
    if not api_key:
        return "⚠️ Erro: Groq API Key não encontrada nos segredos do sistema."

    try:
        # 2. Inicialização do Cliente
        client = Groq(api_key=api_key)

        # 3. Engenharia de Prompt (Contexto de Facilities)
        # O prompt instrui a IA a não apenas ler os dados, mas agir como um consultor.
        system_instruction = (
            "Você é um Especialista em Controladoria de Facilities. Seu papel é analisar "
            "variações Year-over-Year (YoY) e separar o que é ruído estatístico de "
            "perda de produtividade ou economia real."
        )

        user_prompt = f"""
        Analise o resumo financeiro abaixo e gere um relatório de produtividade.

        ### DADOS DE VARIAÇÃO (Resumo dos Itens):
        {data_summary}

        ### CONTEXTO DA NAVEGAÇÃO:
        {context_text}

        ---
        ### INSTRUÇÕES PARA O RELATÓRIO:
        1. **Destaque os Ofensores:** Quais itens ou centros de custo causaram o maior impacto negativo (aumento de custo)?
        2. **Análise de Produtividade:** Onde houve redução de custo? Explique se isso parece ser uma melhoria de processo ou apenas volume menor.
        3. **Anomalias Mensais:** Com base na variação, sugira se há algum mês específico que precise de auditoria.
        4. **Recomendação:** Dê uma sugestão prática de gestão para reduzir custos nesta visão específica.

        Responda de forma concisa, em Markdown, usando negrito para pontos críticos.
        """

        # 4. Chamada ao Modelo Llama 3.3
        # Usamos temperature 0.2 para garantir que a IA não "alucine" valores fora da tabela.
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=1024,
            top_p=1,
            stream=False,
        )

        return completion.choices[0].message.content

    except Exception as e:
        return f"❌ Erro na integração com o motor de IA: {str(e)}"