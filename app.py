# app.py
import streamlit as st
from datetime import datetime
from modules.oauth2 import ContaAzulOAuth2
from modules.smart_analyzer import SmartAnalyzer

# --- CONFIGURAÇÃO E INICIALIZAÇÃO ---
st.set_page_config(page_title="Painel Conta Azul - Análise Inteligente", layout="wide")
oauth = ContaAzulOAuth2()
analyzer = SmartAnalyzer()

# --- FUNÇÕES AUXILIARES ---
@st.cache_data(ttl=3600) # Cache de 1 hora
def carregar_categorias_da_api(_oauth_client, access_token):
    """Busca e armazena em cache a lista completa de categorias de despesa."""
    try:
        params = {"pagina": 1, "tamanho_pagina": 500, "tipo": "DESPESA", "permite_apenas_filhos": "true"}
        response = _oauth_client.make_api_request("categorias", "GET", access_token=access_token, params=params)
        return response.get("itens", []) if response else []
    except Exception as e:
        st.error(f"Erro fatal ao carregar categorias da API: {e}")
        return []

# --- TELA PRINCIPAL E LÓGICA DE AUTENTICAÇÃO ---
st.title("🔵 Painel Conta Azul - Análise Inteligente")

# (O bloco de autenticação da sidebar permanece o mesmo da versão anterior)
# ...

token_data = st.session_state.get('token_data')
if token_data and not oauth.is_token_expired(token_data):
    
    # 1. CARREGA O "MAPA" DE CATEGORIAS UMA ÚNICA VEZ
    lista_categorias = carregar_categorias_da_api(oauth, token_data['access_token'])
    
    if not lista_categorias:
        st.error("Não foi possível carregar as categorias da sua conta. O aplicativo não pode continuar.")
        st.stop()
        
    # 2. MODO INVESTIGADOR (para você ver as categorias disponíveis)
    st.sidebar.markdown("---")
    modo_investigador = st.sidebar.checkbox("🕵️‍♂️ Ativar Modo Investigador de Categorias")
    if modo_investigador:
        st.sidebar.success("Modo Investigador Ativo!")
        st.sidebar.write("Abaixo estão todas as categorias de despesa encontradas na sua conta:")
        st.sidebar.dataframe([cat['nome'] for cat in lista_categorias])

    # 3. INTERFACE DE PERGUNTAS
    st.header("💬 Converse com suas despesas")
    pergunta = st.text_input("Faça sua pergunta:", placeholder="Ex: Quanto gastei com combustível da Hilux este ano?")

    if st.button("Analisar", use_container_width=True) and pergunta:
        with st.spinner("Analisando e consultando a API..."):
            try:
                # 4. ANÁLISE LOCAL E RÁPIDA
                analise = analyzer.analisar_pergunta(pergunta, lista_categorias)
                
                # 5. MONTAGEM PRECISA DOS PARÂMETROS
                params_api = {
                    "data_vencimento_de": "2010-01-01",
                    "data_vencimento_ate": "2035-12-31",
                    "data_competencia_de": analise["data_de"],
                    "data_competencia_ate": analise["data_ate"],
                    "pagina": 1,
                    "tamanho_pagina": 200 
                }
                if analise["categoria_obj"]:
                    params_api["ids_categorias"] = [analise["categoria_obj"]["id"]]
                if analise["descricao_texto"]:
                    params_api["descricao"] = analise["descricao_texto"]
                
                # 6. BUSCA FINAL E EFICIENTE
                dados_api = oauth.make_api_request(
                    endpoint="financeiro/eventos-financeiros/contas-a-pagar/buscar",
                    method="GET",
                    access_token=token_data['access_token'],
                    params=params_api
                )
                
                # 7. EXIBIÇÃO
                st.session_state.last_response = {
                    "resposta_formatada": analyzer.formatar_resposta(dados_api, analise),
                    "analise": analise,
                    "dados_api": dados_api
                }
                st.rerun()

            except Exception as e:
                st.error(f"Ocorreu um erro: {e}")
    
    if 'last_response' in st.session_state:
        response_data = st.session_state.last_response
        st.markdown(response_data["resposta_formatada"])
        with st.expander("🔍 Detalhes da Análise e Resposta da API"):
            st.json({ "Análise da Pergunta": response_data["analise"], "Dados Recebidos": response_data["dados_api"] })
