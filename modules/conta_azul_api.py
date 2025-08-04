class FerramentasContaAzul:
    def __init__(self, oauth_client, access_token):
        self.oauth = oauth_client #
        self.token = access_token #

    def buscar_despesas(self, data_de: str, data_ate: str, categoria_nome: str = None, descricao: str = None):
        """
        Busca despesas (contas a pagar) em um período.
        Pode filtrar por uma 'categoria_nome' precisa ou por uma 'descricao' textual.
        'data_de' e 'data_ate' devem estar no formato 'AAAA-MM-DD'.
        """
        print(f"EXECUTANDO FERRAMENTA: buscar_despesas com data_de={data_de}, data_ate={data_ate}, categoria_nome={categoria_nome}, descricao={descricao}")
        
        params = {
            "data_competencia_de": data_de, #
            "data_competencia_ate": data_ate, #
            "pagina": 1, #
            "tamanho_pagina": 500 # Aumentado para buscar mais resultados
        }

        # Lógica aprimorada para busca por categoria ou descrição
        if categoria_nome:
            print(f"Buscando ID para a categoria: {categoria_nome}")
            # Chama a nova função que adicionamos ao oauth_client
            categoria_id = self.oauth.get_category_id_by_name(categoria_nome, self.token)
            if categoria_id:
                print(f"ID da categoria encontrado: {categoria_id}")
                params["ids_categorias"] = [categoria_id]
            else:
                print(f"ID da categoria não encontrado. Buscando por '{categoria_nome}' na descrição.")
                # Se não encontrar ID, usa o nome da categoria como fallback na descrição
                params["descricao"] = categoria_nome

        # Adiciona a descrição se ela for fornecida e não houver um filtro de categoria mais preciso
        if descricao and "descricao" not in params:
            params["descricao"] = descricao
        
        return self.oauth.make_api_request(
            endpoint="financeiro/eventos-financeiros/contas-a-pagar/buscar", #
            method="GET", #
            access_token=self.token, #
            params=params #
        )
