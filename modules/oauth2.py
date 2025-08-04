# Substitua todo o conteúdo de modules/oauth2.py por este código

import streamlit as st
import requests
import base64
import urllib.parse
from datetime import datetime, timedelta
import pytz
import unicodedata

class ContaAzulOAuth2:
    def __init__(self):
        self.client_id = st.secrets.get("CLIENT_ID") #
        self.client_secret = st.secrets.get("CLIENT_SECRET") #
        self.redirect_uri = st.secrets.get("REDIRECT_URI") #
        self.api_base_url = "https://api-v2.contaazul.com/v1" #
        self.token_url = "https://auth.contaazul.com/oauth2/token" #
        self.auth_url = "https://auth.contaazul.com/oauth2/authorize" #
        self.scope = "openid profile aws.cognito.signin.user.admin" #
        self.timezone = pytz.timezone("America/Araguaina") #

    def _normalize_text(self, text):
        """Função auxiliar para normalizar texto (remove acentos, minúsculas)."""
        if not text: return ""
        return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII').lower().strip()

    def generate_auth_url(self): #
        st.session_state.oauth_state = "34121401" #
        params = { 'response_type': 'code', 'client_id': self.client_id, 'redirect_uri': self.redirect_uri, 'state': st.session_state.oauth_state, 'scope': self.scope } #
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}" #

    def exchange_code_for_token(self, code, state): #
        if state != st.session_state.get("oauth_state"): raise Exception("State inválido") #
        auth_string = f"{self.client_id}:{self.client_secret}" #
        auth_b64 = base64.b64encode(auth_string.encode('ascii')).decode('ascii') #
        headers = { 'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': f'Basic {auth_b64}' } #
        data = { 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': self.redirect_uri } #
        response = requests.post(self.token_url, headers=headers, data=data) #
        response.raise_for_status() #
        token_data = response.json() #
        expires_at = datetime.now(self.timezone) + timedelta(seconds=token_data.get('expires_in', 3600)) #
        token_data['expires_at'] = expires_at.isoformat() #
        return token_data #

    def is_token_expired(self, token_data): #
        if not token_data or 'expires_at' not in token_data: return True #
        return datetime.now(self.timezone) >= datetime.fromisoformat(token_data['expires_at']) #

    def make_api_request(self, endpoint, method='GET', data=None, access_token=None, params=None): #
        if not access_token: raise Exception("Access token é obrigatório") #
        url = f"{self.api_base_url}/{endpoint.lstrip('/')}" #
        headers = { 'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json' } #
        response = requests.request(method, url, headers=headers, params=params, json=data) #
        if not response.ok: #
            print("ERRO NA REQUISIÇÃO:", response.status_code, response.text) #
        response.raise_for_status() #
        return response.json() #

    def get_category_id_by_name(self, category_name_to_find, access_token):
        """Busca o ID de uma categoria pelo nome."""
        if not category_name_to_find:
            return None
        
        # Parâmetros para buscar a categoria na API
        params = {"nome": category_name_to_find, "pagina": 1, "tamanho_pagina": 20}
        
        try:
            response = self.make_api_request(
                endpoint="categorias",
                method="GET",
                access_token=access_token,
                params=params
            )
            if response and response.get("itens"):
                # Normaliza o nome buscado para comparação
                normalized_search_name = self._normalize_text(category_name_to_find)
                for item in response["itens"]:
                    # Compara com o nome normalizado do item retornado pela API
                    if self._normalize_text(item["nome"]) == normalized_search_name:
                        return item["id"]
            return None # Retorna None se não encontrar correspondência exata
        except Exception as e:
            st.error(f"Erro ao buscar ID da categoria '{category_name_to_find}': {e}")
            return None
