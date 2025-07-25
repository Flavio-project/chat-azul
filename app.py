import streamlit as st
from datetime import datetime
from modules.oauth2 import ContaAzulOAuth2
from modules.smart_analyzer import SmartAnalyzer
from modules.config import TIMEZONE
import pytz

TIMEZONE_OBJ = pytz.timezone(TIMEZONE)

def get_current_time():
    return datetime.now(TIMEZONE_OBJ)

oauth = ContaAzulOAuth2()
analyzer = SmartAnalyzer(oauth, caminho_categorias="CATEGORIAS - CONTA AZUL.txt")

st.set_page_config(
    page_title="Painel Conta Azul - Análise Inteligente",
    page_icon="🔵",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔵 Painel Conta Azul - Análise Inteligente")
st.markdown("---")

if not oauth.client_id or not oauth.client_secret:
    st.error("⚠️ **Credenciais não encontradas!** Verifique seu arquivo `.env`.")
    st.stop()

with st.sidebar:
    st.header("🔐 Status OAuth2")
    current_time = get_current_time()
    st.info(f"🕐 Horário: {current_time.strftime('%H:%M:%S')} ({TIMEZONE})")
    query_params = st.query_params
    token_data = st.session_state.get('token_data')

    if token_data and not oauth.is_token_expired(token_data):
        st.success("✅ Autenticado")
        try:
            expires_at = datetime.fromisoformat(token_data['expires_at'])
            st.info(f"Token expira em: {expires_at.strftime('%H:%M:%S')}")
        except:
            st.info("Token Válido")
        if st.button("🚪 Logout"):
            keys_to_delete = ['token_data', 'oauth_state', 'historico']
            for key in keys_to_delete:
                if key in st.session_state:
                    del st.session_state[key]
            st.query_params.clear()
            st.rerun()
    elif 'code' in query_params and 'state' in query_params:
        with st.spinner("Processando autenticação..."):
            try:
                token_data = oauth.exchange_code_for_token(query_params['code'], query_params['state'])
                st.session_state.token_data = token_data
                st.query_params.clear()
                st.success("✅ Autenticação realizada!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erro na autenticação: {e}")
    else:
        st.warning("❌ Não autenticado")
        auth_url = oauth.generate_auth_url()
        st.markdown(f"<a href='{auth_url}' target='_self' style='display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-align: center; text-decoration: none; border-radius: 5px;'>🔑 Fazer Login com Conta Azul</a>", unsafe_allow_html=True)


token_data = st.session_state.get('token_data')
if token_data and not oauth.is_token_expired(token_data):
    st.header("💬 Pergunte sobre suas despesas")
    if 'historico' not in st.session_state:
        st.session_state.historico = []

    # NOVO: MODO DE INVESTIGAÇÃO
    st.sidebar.markdown("---")
    modo_investigacao = st.sidebar.checkbox("🕵️‍♂️ Ativar Modo de Investigação")
    st.sidebar.caption("Ative para ignorar os filtros de categoria/descrição e ver os dados brutos da API para um período.")

    pergunta = st.text_input(
        "Faça sua pergunta:",
        placeholder="Ex: despesas este ano",
        key="pergunta_input"
    )

    if st.button("📤 Enviar", use_container_width=True) and pergunta:
        with st.spinner("Buscando e analisando dados..."):
            try:
                analise = analyzer.analisar_pergunta(pergunta)
                
                params_api = {
                    "data_vencimento_de": "2010-01-01",
                    "data_vencimento_ate": "2035-12-31",
                    "data_competencia_de": analise["data_de"],
                    "data_competencia_ate": analise["data_ate"],
                    "pagina": 1,
                    "tamanho_pagina": 1000
                }

                # Se o modo de investigação NÃO estiver ativo, aplica os filtros
                if not modo_investigacao:
                    categoria_id = None
                    if analise["categoria_nome"]:
                        categoria_id = oauth.get_category_id_by_name(analise["categoria_nome"], token_data['access_token'])
                    
                    if categoria_id:
                        params_api["ids_categorias"] = [categoria_id]
                    if analise["descricao_texto"]:
                        params_api["descricao"] = analise["descricao_texto"]

                dados_api = oauth.make_api_request(
                    endpoint="financeiro/eventos-financeiros/contas-a-pagar/buscar",
                    method="GET",
                    access_token=token_data['access_token'],
                    params=params_api
                )

                resposta_formatada = analyzer.formatar_resposta(dados_api, analise)
                
                resposta = { "resposta": resposta_formatada, "analise": analise, "dados_brutos": dados_api }

            except Exception as e:
                resposta = {"erro": str(e)}

            st.session_state.historico.insert(0, {"tipo": "pergunta", "conteudo": pergunta})
            st.session_state.historico.insert(1, {"tipo": "resposta", "conteudo": resposta, "modo_investigacao": modo_investigacao})
            st.rerun()

    if st.session_state.historico:
        st.subheader("💬 Histórico da Conversa")
        item = st.session_state.historico[1] # Apenas a última resposta
        pergunta_item = st.session_state.historico[0]

        st.markdown(f"**🙋 Você:** {pergunta_item['conteudo']}")
        
        resposta = item["conteudo"]
        if "erro" in resposta:
            st.error(f"❌ Erro: {resposta['erro']}")
        else:
            if item["modo_investigacao"]:
                st.warning("🕵️‍♂️ Modo de Investigação Ativo: Exibindo dados sem filtro de categoria/descrição.")
            
            st.markdown(f"**🤖 Conta Azul:**\n{resposta['resposta']}")
            
            with st.expander("📊 Detalhes técnicos e Dados Brutos da API"):
                st.json({
                    "analise_da_pergunta": resposta.get('analise'),
                    "dados_recebidos": resposta.get('dados_brutos')
                })