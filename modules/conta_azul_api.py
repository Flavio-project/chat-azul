# Este arquivo define as "ferramentas" que a IA pode usar.
# Cada função corresponde a um endpoint da API da Conta Azul.

class FerramentasContaAzul:
    def __init__(self, oauth_client, access_token):
        self.oauth = oauth_client
        self.token = access_token

    def buscar_despesas(self, data_de: str, data_ate: str, descricao: str = None):
        """
        Busca despesas (contas a pagar) em um período. Pode filtrar por uma descrição.
        Use esta ferramenta para perguntas sobre gastos, custos ou despesas gerais.
        'data_de' e 'data_ate' devem estar no formato 'AAAA-MM-DD'.
        """
        print(f"EXECUTANDO FERRAMENTA: buscar_despesas com data_de={data_de}, data_ate={data_ate}, descricao={descricao}")
        params = {
            "data_vencimento_de": "2010-01-01",
            "data_vencimento_ate": "2035-12-31",
            "data_competencia_de": data_de,
            "data_competencia_ate": data_ate,
            "pagina": 1,
            "tamanho_pagina": 200
        }
        if descricao:
            params["descricao"] = descricao
        
        return self.oauth.make_api_request(
            endpoint="financeiro/eventos-financeiros/contas-a-pagar/buscar",
            method="GET",
            access_token=self.token,
            params=params
        )

    # NO FUTURO, PODEMOS ADICIONAR MAIS FERRAMENTAS AQUI
    # Ex: def obter_detalhes_parcela(id_parcela: str): ...
