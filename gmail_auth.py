import os
import logging
import socket
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Nastavení delšího timeoutu pro pomalejší připojení (10 minut)
socket.setdefaulttimeout(600)

# Google Auth knihovny
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import dotenv

dotenv.load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose'
]

def get_gmail_service(log_level=logging.INFO):
    """
    Získá Gmail službu. Robustní verze s manuálním fallbackem a dlouhým timeoutem.
    """
    # Nastavení loggeru
    logger = logging.getLogger("gmail_auth")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        ch = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    creds = None
    script_dir = Path(__file__).parent
    token_path = script_dir / "token.json"

    # --- Načtení ENV ---
    env_client_id = os.getenv("GOOGLE_CLIENT_ID_env")
    env_client_secret = os.getenv("GOOGLE_CLIENT_SECRET_env")
    env_refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN_env")
    env_creds_filename = os.getenv("GOOGLE_CREDENTIALS_NAME_env")
    
    # 1. Environment variables
    if env_client_id and env_client_secret and env_refresh_token:
        logger.info("🔑 Používám credentials z ENV.")
        creds = Credentials(
            token=None,
            refresh_token=env_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=env_client_id,
            client_secret=env_client_secret,
            scopes=SCOPES
        )

    # 2. Existující token.json
    elif token_path.exists():
        logger.info(f"📂 Načítám existující token: {token_path}")
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception as e:
            logger.warning(f"Token soubor je poškozený: {e}")

    # 3. Refresh
    if creds and not creds.valid:
        if creds.expired and creds.refresh_token:
            logger.info("⟳ Token expiroval, provádím refresh...")
            try:
                creds.refresh(Request())
            except Exception:
                logger.warning("Refresh selhal.")
                creds = None

    # 4. Manuální autorizace (Copy-Paste)
    if not creds:
        logger.info("🌐 Spouštím manuální OAuth flow...")

        # Konfigurace Flow
        if env_client_id and env_client_secret:
            config = {
                "installed": {
                    "client_id": env_client_id,
                    "client_secret": env_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:8080/"]
                }
            }
            flow = InstalledAppFlow.from_client_config(config, SCOPES)
        else:
            secret_file = None
            if env_creds_filename and (script_dir / env_creds_filename).exists():
                secret_file = script_dir / env_creds_filename
            elif list(script_dir.glob("client_secret_*.json")):
                secret_file = list(script_dir.glob("client_secret_*.json"))[0]
            
            if not secret_file:
                raise FileNotFoundError("❌ Chybí credentials.")
            
            logger.info(f"Používám soubor: {secret_file.name}")
            flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)

        flow.redirect_uri = "http://localhost:8080/"
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

        print("\n" + "="*80)
        print("⚠️  MANUÁLNÍ AUTORIZACE:")
        print(f"\n{auth_url}\n")
        print("="*80 + "\n")

        try:
            auth_response = input("📝 Vložte zkopírovanou URL (http://localhost...) a dejte ENTER: ").strip()
        except OSError:
             logger.error("Nelze číst vstup. Spusťte skript interaktivně.")
             raise

        try:
            parsed_url = urlparse(auth_response)
            params = parse_qs(parsed_url.query)
            
            if 'code' not in params:
                if auth_response.startswith("4/"):
                    code = auth_response
                else:
                    raise ValueError("URL neobsahuje 'code'.")
            else:
                code = params['code'][0]

            flow.fetch_token(code=code)
            creds = flow.credentials
            
            logger.info("💾 Ukládám nový token do token.json")
            with open(token_path, "w") as token:
                token.write(creds.to_json())
                
        except Exception as e:
            logger.error(f"❌ Chyba: {e}")
            raise

    logger.info("✅ Vytvářím Gmail API klienta.")
    # Zde se ještě nic neposílá po síti, jen se staví objekt
    service = build("gmail", "v1", credentials=creds)
    return service

if __name__ == "__main__":
    try:
        service = get_gmail_service()
        print("⏳ Testuji spojení s API (to může chvíli trvat)...")
        profile = service.users().getProfile(userId='me').execute()
        print(f"🎉 ÚSPĚCH! Přihlášen jako: {profile['emailAddress']}")
    except Exception as e:
        print(f"💥 CHYBA: {e}")