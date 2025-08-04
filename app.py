import streamlit as st
from datetime import date, datetime
from modules.oauth2 import ContaAzulOAuth2
from modules.conta_azul_api import FerramentasContaAzul
from openai import OpenAI
import json
import pytz

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Painel Inteligente Conta Azul", layout="wide") #
oauth = ContaAzulOAuth2() #
TIMEZONE = "America/Araguaina" #
TIMEZONE_OBJ = pytz.timezone(TIMEZONE) #

# Carrega a lista de categorias uma vez para usar no prompt
try:
    with open("CATEGORIAS - CONTA AZUL.txt", "r", encoding="utf-8") as f:
        lista_categorias = f.read()
except FileNotFoundError:
    st.error("Arquivo 'CATEGORIAS - CONTA AZUL.txt' não encontrado.")
    lista_categorias = "Nenhuma categoria carregada."


# --- FUNÇÕES PRINCIPAIS ---
def executar_plano_da_ia(plano, ferramentas): #
    nome_ferramenta = plano.get("ferramenta") #
    argumentos = plano.get("argumentos", {}) #
    
    if hasattr(ferramentas, nome_ferramenta): #
        funcao = getattr(ferramentas, nome_ferramenta) #
        return funcao(**argumentos) #
    else: #
        raise ValueError(f"Ferramenta desconhecida: {nome_ferramenta}") #

# --- INTERFACE E LÓGICA DE AUTENTICAÇÃO ---
st.title("🔵 Painel Inteligente Conta Azul (v.IA com Categorias)") #

if not st.secrets.get("CLIENT_ID") or not st.secrets.get("CLIENT_SECRET"): #
    st.error("As credenciais da Conta Azul não foram configuradas nos Segredos (Secrets) do Streamlit.") #
    st.stop() #

# --- BLOCO DE AUTENTICAÇÃO NA SIDEBAR ---
with st.sidebar: #
    st.header("🔐 Status OAuth2") #
    current_time = datetime.now(TIMEZONE_OBJ) #
    st.info(f"🕐 Horário: {current_time.strftime('%H:%M:%S')} ({TIMEZONE})") #
    query_params = st.query_params #
    token_data = st.session_state.get('token_data') #

    if token_data and not oauth.is_token_expired(token_data): #
        st.success("✅ Autenticado") #
        if st.button("🚪 Logout"): #
            keys_to_delete = ['token_data', 'oauth_state', 'last_response'] #
            for key in keys_to_delete: #
                if key in st.session_state: del st.session_state[key] #
            st.query_params.clear() #
            st.rerun() #
    elif 'code' in query_params and 'state' in query_params: #
        with st.spinner("Processando autenticação..."): #
            try:
                code = query_params['code'][0] #
                state = query_params['state'][0] #
                token_data = oauth.exchange_code_for_token(code, state) #
                st.session_state.token_data = token_data #
                st.query_params.clear() #
                st.rerun() #
            except Exception as e:
                st.error(f"❌ Erro na autenticação: {e}") #
    else: #
        st.warning("❌ Não autenticado") #
        auth_url = oauth.generate_auth_url() #
        st.markdown(f"<a href='{auth_url}' target='_self' style='...'>🔑 Fazer Login com Conta Azul</a>", unsafe_allow_html=True) #

# --- LÓGICA PRINCIPAL DA APLICAÇÃO (APÓS LOGIN) ---
token_data = st.session_state.get('token_data') #
if token_data and not oauth.is_token_expired(token_data): #
    st.sidebar.title("Configuração da IA") #
    api_key_input = st.sidebar.text_input("Sua Chave de API da OpenAI", type="password", value=st.secrets.get("OPENAI_API_KEY", "")) #

    st.header("💬 Converse com suas finanças") #
    pergunta = st.text_input("O que você gostaria de saber?", placeholder="Ex: Quanto gastei com combustível no mês passado?") #

    if st.button("Perguntar à IA", use_container_width=True) and pergunta: #
        if not api_key_input: #
            st.error("Por favor, insira sua chave de API da OpenAI na barra lateral.") #
        else: #
            try:
                client = OpenAI(api_key=api_key_input) #
                ferramentas = FerramentasContaAzul(oauth, token_data['access_token']) #

                with st.spinner("IA está analisando e planejando..."): #
                    prompt = f"""
                    Você é um assistente financeiro especialista na API da Conta Azul.
                    Sua tarefa é converter a pergunta do usuário em um plano de ação para chamar a ferramenta correta.
                    A pergunta do usuário é: "{pergunta}"
                    Hoje é {date.today().strftime('%Y-%m-%d')}.

                    Você tem acesso à seguinte ferramenta:
                    - `buscar_despesas(data_de, data_ate, categoria_nome=None, descricao=None)`: Busca despesas. Use `categoria_nome` para buscas precisas por categoria e `descricao` para filtrar por texto livre.

                    A lista de categorias de despesa disponíveis é:
                    ---
                    {lista_categorias}
                    ---

                    Analise a pergunta e identifique a **categoria exata** da lista acima. Se a pergunta não parece se referir a uma categoria específica, deixe `categoria_nome` como null e use os termos da busca em `descricao`.
                    Sempre preencha 'data_de' e 'data_ate' no formato 'AAAA-MM-DD'.
                    
                    Responda APENAS com um objeto JSON.
                    Exemplo de pergunta: "gastos com frete este ano"
                    Resposta JSON esperada:
                    {{
                      "ferramenta": "buscar_despesas",
                      "argumentos": {{
                        "data_de": "{date.today().year}-01-01",
                        "data_ate": "{date.today().strftime('%Y-%m-%d')}",
                        "categoria_nome": "FRETES ENCOMENDAS",
                        "descricao": null
                      }}
                    }}
                    """
                    response_ia = client.chat.completions.create(
                        model="gpt-4o-mini", #
                        messages=[{"role": "user", "content": prompt}], #
                        response_format={"type": "json_object"} #
                    )
                    plano_ia = json.loads(response_ia.choices[0].message.content) #

                with st.spinner("Executando o plano e buscando dados..."): #
                    dados_api = executar_plano_da_ia(plano_ia, ferramentas) #

                with st.spinner("IA está resumindo os resultados..."): #
                    prompt_resumo = f"""
                    Você é um assistente financeiro.
                    A pergunta original do usuário foi: "{pergunta}"
                    Os dados brutos da API são: {json.dumps(dados_api.get("itens", []), indent=2, ensure_ascii=False)}

                    Resuma os dados de forma clara e amigável em português.
                    Comece com o valor total e o número de lançamentos.
                    Depois, se houver itens, liste os 5 primeiros exemplos.
                    Se não houver itens, diga que nada foi encontrado para os filtros.
                    """
                    response_resumo = client.chat.completions.create(
                        model="gpt-4o-mini", #
                        messages=[{"role": "user", "content": prompt_resumo}] #
                    )
                    resumo_final = response_resumo.choices[0].message.content #
                
                st.session_state.last_response = { "resumo": resumo_final, "plano": plano_ia, "dados": dados_api } #
                st.rerun() #

            except Exception as e: #
                st.error(f"Ocorreu um erro: {e}") #

    if 'last_response' in st.session_state: #
        response = st.session_state.last_response #
        st.markdown("### Resposta da IA") #
        st.markdown(response["resumo"]) #
        with st.expander("🔍 Detalhes da Execução"): #
            st.write("**Plano gerado pela IA:**") #
            st.json(response["plano"]) #
            st.write("**Dados brutos recebidos da Conta Azul:**") #
            st.json(response["dados"]) #
