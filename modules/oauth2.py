import unicodedata
import requests
import base64
import urllib.parse
from datetime import datetime, timedelta
import pytz
import os
from modules.config import CLIENT_ID, CLIENT_SECRET, EMPRESA_ID, REDIRECT_URI, AUTH_URL, TOKEN_URL, API_BASE_URL, SCOPE, TIMEZONE

TIMEZONE_OBJ = pytz.timezone(TIMEZONE)

def get_current_time():
    return datetime.now(TIMEZONE_OBJ)

class ContaAzulOAuth2:
    def __init__(self):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.empresa_id = EMPRESA_ID
        self.redirect_uri = REDIRECT_URI
        self.auth_url = AUTH_URL
        self.token_url = TOKEN_URL
        self.api_base_url = API_BASE_URL
        self.scope = SCOPE

    def generate_auth_url(self):
        state = "34121401"
        import streamlit as st
        st.session_state.oauth_state = state
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'state': state,
            'scope': self.scope
        }
        return f"{self.auth_url}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_token(self, code, state):
        if state != "34121401":
            raise Exception("State inválido - possível ataque CSRF")
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_b64 = base64.b64encode(auth_string.encode('ascii')).decode('ascii')
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {auth_b64}'
        }
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri
        }
        response = requests.post(self.token_url, headers=headers, data=data)
        response.raise_for_status()
        token_data = response.json()
        expires_at = get_current_time() + timedelta(seconds=token_data.get('expires_in', 3600))
        token_data['expires_at'] = expires_at.isoformat()
        return token_data

    def refresh_access_token(self, refresh_token):
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_b64 = base64.b64encode(auth_string.encode('ascii')).decode('ascii')
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {auth_b64}'
        }
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        response = requests.post(self.token_url, headers=headers, data=data)
        response.raise_for_status()
        token_data = response.json()
        expires_at = get_current_time() + timedelta(seconds=token_data.get('expires_in', 3600))
        token_data['expires_at'] = expires_at.isoformat()
        return token_data

    def is_token_expired(self, token_data):
        if not token_data or 'expires_at' not in token_data:
            return True
        try:
            expires_at = datetime.fromisoformat(token_data['expires_at'])
            if expires_at.tzinfo is None:
                expires_at = TIMEZONE_OBJ.localize(expires_at)
            return get_current_time() >= expires_at
        except:
            return True

    def make_api_request(self, endpoint, method='GET', data=None, access_token=None, params=None):
        if not access_token:
            raise Exception("Access token é obrigatório")
        url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == 'PUT':
            response = requests.put(url, headers=headers, json=data)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            raise Exception(f"Método HTTP não suportado: {method}")
        
        if not response.ok:
            print("ERRO NA REQUISIÇÃO:", response.status_code, response.text)

        response.raise_for_status()
        return response.json()

    def get_category_id_by_name(self, category_name, access_token):
        if not category_name:
            return None
        
        params = { "busca": category_name, "pagina": 1, "tamanho_pagina": 10, "permite_apenas_filhos": "true" }
        try:
            response = self.make_api_request( endpoint="categorias", method="GET", access_token=access_token, params=params )
            if response and response.get("itens"):
                for item in response["itens"]:
                    if normalizar(item["nome"]) == normalizar(category_name):
                        return item["id"]
                # Se não encontrar uma correspondência exata, não retorna nada para evitar erros.
                return None
        except Exception as e:
            print(f"Erro ao buscar ID da categoria '{category_name}': {e}")
            return None

def normalizar(texto):
    if not texto: return ""
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII').lower().strip()