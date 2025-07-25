# app.py
import streamlit as st
from datetime import datetime, date
from modules.oauth2 import ContaAzulOAuth2
from openai import OpenAI
import json

# --- CONFIGURAÇÃO E INICIALIZAÇÃO ---
st.set_page_config(page_title="Painel Conta Azul com IA", layout="wide")
oauth = ContaAzulOAuth2()

# --- FUNÇÕES AUXILIARES ---
@st.cache_data(ttl=3600) # Cache de 1 hora para a lista de categorias
def get_all_categories(_oauth_client, access_token):
    """Busca todas as categorias de despesa da conta do usuário."""
    try:
        todas_categorias = []
        params = {"pagina": 1, "tamanho_pagina": 200, "tipo": "DESPESA", "permite_apenas_filhos": "true"}
        response = _oauth_client.make_api_request("categorias", "GET", access_token=access_token, params=params)
        if response and response.get("itens"):
            todas_categorias.extend([cat['nome'] for cat in response['itens']])
        return todas_categorias
    except Exception as e:
        st.error(f"Não foi possível buscar a lista de categorias: {e}")
        return []

def formatar_resposta_final(dados_api, analise_ia):
    """Formata a resposta final para o usuário."""
    if not dados_api or not dados_api.get("itens"):
        return "❌ Nenhum gasto encontrado para os filtros informados pela IA."
    
    itens = dados_api["itens"]
    total_gasto = sum(float(item.get("total", 0)) for item in itens)
    
    resposta = f"💸 **Total de gastos encontrado: R$ {total_gasto:,.2f}**\n"
    resposta += f"📝 **{len(itens)}** lançamentos encontrados.\n\n"

    for item in itens[:10]: # Exibe os 10 primeiros
        data = item.get("data_competencia", item.get("data_vencimento", ""))
        desc = item.get("descricao", "Sem descrição")
        valor = float(item.get("total", 0))
        resposta += f"- *{data}*: {desc} (R$ {valor:,.2f})\n"
    
    return resposta

# --- TELA PRINCIPAL E LÓGICA DE AUTENTICAÇÃO ---
st.title("🔵 Painel Conta Azul com IA (GPT-4o Mini)")

# Bloco de autenticação (semelhante ao anterior)
# ... (código de autenticação na sidebar) ...

# --- APLICAÇÃO PRINCIPAL (APÓS LOGIN) ---
token_data = st.session_state.get('token_data')
if token_data and not oauth.is_token_expired(token_data):
    
    st.sidebar.title("Configuração da IA")
    api_key_input = st.sidebar.text_input("Sua Chave de API da OpenAI", type="password")

    # Busca e armazena a lista de categorias no cache
    lista_categorias = get_all_categories(oauth, token_data['access_token'])

    st.header("💬 Converse com suas despesas")
    pergunta = st.text_input("Faça sua pergunta:", placeholder="Ex: Quanto gastei com combustível da Hilux este ano?")

    if st.button("Analisar com IA", use_container_width=True) and pergunta:
        if not api_key_input:
            st.error("Por favor, insira sua chave de API da OpenAI na barra lateral.")
        else:
            try:
                client = OpenAI(api_key=api_key_input)
                
                with st.spinner("A IA está analisando sua pergunta..."):
                    prompt = f"""
                    Sua tarefa é converter uma pergunta de um usuário em um JSON para filtrar uma API de despesas.
                    A pergunta é: "{pergunta}"
                    Hoje é {date.today().strftime('%Y-%m-%d')}.
                    As categorias de despesa existentes são: {lista_categorias}.
                    
                    Você DEVE retornar APENAS um objeto JSON com as seguintes chaves:
                    - "data_competencia_de": string no formato "YYYY-MM-DD". Se não especificado, use o início do ano atual.
                    - "data_competencia_ate": string no formato "YYYY-MM-DD". Se não especificado, use a data de hoje.
                    - "ids_categorias": uma LISTA de strings com os nomes EXATOS das categorias encontradas na lista fornecida. Se nenhuma for encontrada, retorne uma lista vazia [].
                    - "descricao": uma string com termos de busca para a descrição da despesa. Se não houver, retorne null.
                    
                    Exemplo: Se a pergunta for "gastos com manutenção da hilux no mês passado", e hoje for 2025-07-25, o JSON seria:
                    {{
                      "data_competencia_de": "2025-06-01",
                      "data_competencia_ate": "2025-06-30",
                      "ids_categorias": ["MANUTENÇÃO HILUX"],
                      "descricao": "hilux"
                    }}
                    """
                    
                    response_ia = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0
                    )
                    analise_ia = json.loads(response_ia.choices[0].message.content)

                with st.spinner("Buscando dados na Conta Azul..."):
                    params_api = {
                        "data_vencimento_de": "2010-01-01",
                        "data_vencimento_ate": "2035-12-31",
                        "pagina": 1,
                        "tamanho_pagina": 200
                    }
                    params_api.update(analise_ia) # Adiciona os filtros da IA

                    # Busca o ID da categoria, se a IA encontrou um nome
                    if analise_ia.get("ids_categorias"):
                        ids_encontrados = []
                        for nome_cat in analise_ia["ids_categorias"]:
                            # Esta função agora está dentro da classe OAuth2
                            id_cat = oauth.get_category_id_by_name(nome_cat, token_data['access_token'])
                            if id_cat:
                                ids_encontrados.append(id_cat)
                        
                        if ids_encontrados:
                            params_api["ids_categorias"] = ids_encontrados

                    dados_api = oauth.make_api_request(
                        endpoint="financeiro/eventos-financeiros/contas-a-pagar/buscar",
                        method="GET",
                        access_token=token_data['access_token'],
                        params=params_api
                    )
                
                st.session_state.last_response = {
                    "resposta_formatada": formatar_resposta_final(dados_api, analise_ia),
                    "analise_ia": analise_ia,
                    "dados_api": dados_api
                }
                st.rerun()

            except Exception as e:
                st.error(f"Ocorreu um erro: {e}")
    
    if 'last_response' in st.session_state:
        response_data = st.session_state.last_response
        st.markdown(response_data["resposta_formatada"])
        with st.expander("🔍 Detalhes da Análise da IA e Resposta da API"):
            st.json({
                "Análise da IA": response_data["analise_ia"],
                "Dados Recebidos da Conta Azul": response_data["dados_api"]
            })
