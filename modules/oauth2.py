# modules/oauth2.py
import requests
import base64
import urllib.parse
from datetime import datetime, timedelta
import pytz
from modules.config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, AUTH_URL, TOKEN_URL, API_BASE_URL, SCOPE, TIMEZONE

TIMEZONE_OBJ = pytz.timezone(TIMEZONE)

class ContaAzulOAuth2:
    def __init__(self):
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
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
        if state != "34121401": raise Exception("State inválido")
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
        expires_at = datetime.now(TIMEZONE_OBJ) + timedelta(seconds=token_data.get('expires_in', 3600))
        token_data['expires_at'] = expires_at.isoformat()
        return token_data

    def is_token_expired(self, token_data):
        if not token_data or 'expires_at' not in token_data: return True
        return datetime.now(TIMEZONE_OBJ) >= datetime.fromisoformat(token_data['expires_at'])

    def make_api_request(self, endpoint, method='GET', data=None, access_token=None, params=None):
        if not access_token: raise Exception("Access token é obrigatório")
        url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
        headers = { 'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json' }
        response = requests.request(method, url, headers=headers, params=params, json=data)
        if not response.ok:
            print("ERRO NA REQUISIÇÃO:", response.status_code, response.text)
        response.raise_for_status()
        return response.json()
