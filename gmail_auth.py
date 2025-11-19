import os
import logging
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import dotenv

# Načtení proměnných z .env souboru
dotenv.load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose'
]

def get_gmail_service(log_level=logging.INFO):
    """
    Hlavní funkce pro získání Gmail API služby.
    Řeší kompletní životní cyklus autentizace:
    1. Environment variables (priorita)
    2. Uložený token.json
    3. Interaktivní přihlášení v prohlížeči
    """
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)

    creds = None
    script_dir = Path(__file__).parent
    token_path = script_dir / "token.json"

    # --- Načtení konfigurace z ENV ---
    env_client_id = os.getenv("GOOGLE_CLIENT_ID_env")
    env_client_secret = os.getenv("GOOGLE_CLIENT_SECRET_env")
    env_refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN_env")
    env_access_token = os.getenv("GOOGLE_ACCESS_TOKEN_env") # Volitelné
    env_creds_filename = os.getenv("GOOGLE_CREDENTIALS_NAME_env") # Např. client_secret.json
    
    # Standardní endpointy (obvykle se nemění)
    token_uri = "https://oauth2.googleapis.com/token"
    
    # ---------------------------------------------------------
    # KROK 1: Zkusíme sestavit credentials přímo z ENV
    # ---------------------------------------------------------
    if env_client_id and env_client_secret and env_refresh_token:
        logger.info("🔑 Používám credentials z environmentálních proměnných.")
        creds = Credentials(
            token=env_access_token, # Může být None, obnoví se přes refresh_token
            refresh_token=env_refresh_token,
            token_uri=token_uri,
            client_id=env_client_id,
            client_secret=env_client_secret,
            scopes=SCOPES
        )

    # ---------------------------------------------------------
    # KROK 2: Pokud nejsou v ENV, zkusíme načíst token.json
    # ---------------------------------------------------------
    elif token_path.exists():
        logger.info(f"📂 Načítám existující token: {token_path}")
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception as e:
            logger.warning(f"Token soubor je poškozený: {e}")

    # ---------------------------------------------------------
    # KROK 3: Validace a případný Refresh
    # ---------------------------------------------------------
    if creds and not creds.valid:
        if creds.expired and creds.refresh_token:
            logger.info("⟳ Token expiroval, provádím refresh...")
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Chyba při refreshování tokenu: {e}")
                creds = None # Refresh selhal, musíme provést novou autorizaci

    # ---------------------------------------------------------
    # KROK 4: Pokud stále nemáme creds, spustíme Browser Flow
    # ---------------------------------------------------------
    if not creds:
        logger.info("🌐 Spouštím interaktivní OAuth flow (otevře se prohlížeč)...")
        
        # a) Získáme konfiguraci klienta (Client Secret)
        client_config = None
        
        # Varianta A: Máme ID a Secret v proměnných, ale chybí refresh token -> vyrobíme config in-memory
        if env_client_id and env_client_secret:
            client_config = {
                "installed": {
                    "client_id": env_client_id,
                    "client_secret": env_client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": token_uri,
                    "redirect_uris": ["http://localhost:8080/"]
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        
        # Varianta B: Hledáme soubor client_secret
        else:
            secret_file = None
            if env_creds_filename:
                # Pokud je název souboru v ENV
                possible_path = script_dir / env_creds_filename
                if possible_path.exists():
                    secret_file = possible_path
            
            if not secret_file:
                # Auto-discovery: najdi první soubor začínající na client_secret_
                files = list(script_dir.glob("client_secret_*.json"))
                if files:
                    secret_file = files[0]
            
            if not secret_file:
                raise FileNotFoundError("❌ Nenalezeny credentials! Nastavte .env nebo vložte client_secret_*.json.")
            
            logger.info(f"Používám soubor s credentials: {secret_file.name}")
            flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)

        # b) Spustíme lokální server pro autorizaci
        # Důležité: port 8080 musí odpovídat nastavení v Google Cloud Console
        creds = flow.run_local_server(
            port=8080,
            open_browser=True,
            prompt='consent', # Vynutí získání refresh tokenu
            access_type='offline'
        )

        # c) Uložíme nový token pro příště
        logger.info("💾 Ukládám nový token do token.json")
        with open(token_path, "w") as token:
            token.write(creds.to_json())

    # ---------------------------------------------------------
    # KROK 5: Vytvoření služby
    # ---------------------------------------------------------
    logger.info("✅ Vytvářím Gmail API klienta.")
    service = build("gmail", "v1", credentials=creds)
    return service

# Pokud spustíte tento soubor přímo, pouze provede autorizaci (test)
if __name__ == "__main__":
    try:
        service = get_gmail_service(logging.DEBUG)
        print("SUCCESS: Služba je připravena.")
        # Testovací volání
        profile = service.users().getProfile(userId='me').execute()
        print(f"Přihlášen jako: {profile['emailAddress']}")
    except Exception as e:
        print(f"FAILURE: {e}")