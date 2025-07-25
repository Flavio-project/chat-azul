import streamlit as st
from datetime import date
from modules.oauth2 import ContaAzulOAuth2
from modules.conta_azul_api import FerramentasContaAzul
from openai import OpenAI
import json

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Painel Inteligente Conta Azul", layout="wide")
oauth = ContaAzulOAuth2()

# --- FUNÇÕES PRINCIPAIS ---
def executar_plano_da_ia(plano, ferramentas):
    nome_ferramenta = plano.get("ferramenta")
    argumentos = plano.get("argumentos", {})
    
    if hasattr(ferramentas, nome_ferramenta):
        funcao = getattr(ferramentas, nome_ferramenta)
        return funcao(**argumentos)
    else:
        raise ValueError(f"Ferramenta desconhecida: {nome_ferramenta}")

# --- INTERFACE E LÓGICA DE AUTENTICAÇÃO ---
st.title("🔵 Painel Inteligente Conta Azul (v.IA)")

# Bloco de autenticação (igual ao anterior, mas agora lê dos secrets)
if not st.secrets.get("CLIENT_ID") or not st.secrets.get("CLIENT_SECRET"):
    st.error("As credenciais da Conta Azul não foram configuradas nos Segredos (Secrets) do Streamlit.")
    st.stop()

with st.sidebar:
    # ... (cole aqui o bloco `with st.sidebar:` da nossa penúltima versão do app.py) ...
    # Ele já está correto e não precisa de mudanças.

# --- LÓGICA PRINCIPAL DA APLICAÇÃO ---
token_data = st.session_state.get('token_data')
if token_data and not oauth.is_token_expired(token_data):
    st.sidebar.title("Configuração da IA")
    api_key_input = st.sidebar.text_input("Sua Chave de API da OpenAI", type="password", value=st.secrets.get("OPENAI_API_KEY", ""))

    st.header("💬 Converse com suas finanças")
    pergunta = st.text_input("O que você gostaria de saber?", placeholder="Ex: Quanto gastei com combustível no mês passado?")

    if st.button("Perguntar à IA", use_container_width=True) and pergunta:
        if not api_key_input:
            st.error("Por favor, insira sua chave de API da OpenAI na barra lateral.")
        else:
            try:
                client = OpenAI(api_key=api_key_input)
                ferramentas = FerramentasContaAzul(oauth, token_data['access_token'])

                with st.spinner("IA está analisando e planejando..."):
                    prompt = f"""
                    Você é um assistente financeiro especialista na API da Conta Azul.
                    Sua tarefa é converter a pergunta do usuário em um plano de ação para chamar a ferramenta correta.
                    A pergunta do usuário é: "{pergunta}"
                    Hoje é {date.today().strftime('%Y-%m-%d')}.

                    Você tem acesso à seguinte ferramenta:
                    - `buscar_despesas(data_de, data_ate, descricao)`: Busca despesas em um período.

                    Responda APENAS com um objeto JSON indicando a ferramenta e seus argumentos.
                    Exemplo de pergunta: "gastos com frete este ano"
                    Exemplo de resposta JSON:
                    {{
                      "ferramenta": "buscar_despesas",
                      "argumentos": {{
                        "data_de": "{date.today().year}-01-01",
                        "data_ate": "{date.today().strftime('%Y-%m-%d')}",
                        "descricao": "frete"
                      }}
                    }}
                    """
                    response_ia = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"}
                    )
                    plano_ia = json.loads(response_ia.choices[0].message.content)

                with st.spinner("Executando o plano e buscando dados..."):
                    dados_api = executar_plano_da_ia(plano_ia, ferramentas)

                with st.spinner("IA está resumindo os resultados..."):
                    prompt_resumo = f"""
                    Você é um assistente financeiro.
                    A pergunta original do usuário foi: "{pergunta}"
                    Os dados brutos da API são: {json.dumps(dados_api.get("itens", []), indent=2)}

                    Resuma os dados de forma clara e amigável para o usuário.
                    Comece com o valor total e o número de lançamentos.
                    Depois, se houver poucos itens, liste alguns exemplos.
                    Se não houver itens, diga que nada foi encontrado para os filtros.
                    """
                    response_resumo = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt_resumo}]
                    )
                    resumo_final = response_resumo.choices[0].message.content
                
                st.session_state.last_response = { "resumo": resumo_final, "plano": plano_ia, "dados": dados_api }
                st.rerun()

            except Exception as e:
                st.error(f"Ocorreu um erro: {e}")

    if 'last_response' in st.session_state:
        response = st.session_state.last_response
        st.markdown(response["resumo"])
        with st.expander("🔍 Detalhes da Execução"):
            st.write("**Plano gerado pela IA:**")
            st.json(response["plano"])
            st.write("**Dados brutos recebidos da Conta Azul:**")
            st.json(response["dados"])
