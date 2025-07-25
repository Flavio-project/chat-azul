import os
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
EMPRESA_ID = os.getenv("EMPRESA_ID")
REDIRECT_URI = "https://excited-verified-sunbird.ngrok-free.app"
AUTH_URL = "https://auth.contaazul.com/oauth2/authorize"
TOKEN_URL = "https://auth.contaazul.com/oauth2/token"
API_BASE_URL = "https://api-v2.contaazul.com/v1"
SCOPE = "openid profile aws.cognito.signin.user.admin"
TIMEZONE = "America/Araguaina"