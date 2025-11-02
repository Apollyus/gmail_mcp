import logging
import os
import json  # <- Přidáno pro parsování JSONu při chybě
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from oauth2client.client import Credentials as OAuth2Credentials # Přejmenováno pro přehlednost
from googleapiclient.discovery import build
from googleapiclient import errors as google_api_errors
import httplib2
import dotenv
from pathlib import Path
from google.oauth2.credentials import Credentials # Toto je novější knihovna
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

dotenv.load_dotenv()

GMAIL_CREDENTIALS_NAME = os.getenv('GMAIL_CREDENTIALS_NAME')

# Path to credentials.json which should contain a JSON document such as:
# ... (komentáře k formátu JSON) ...
# Ostatní funkce (např. exchange_code) budou stále používat CLIENTSECRETS_LOCATION
# jak bylo v původním kódu.
CLIENTSECRETS_LOCATION = GMAIL_CREDENTIALS_NAME
REDIRECT_URI = 'http://localhost:8080/'  # Adjust to your redirect URI.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose'
]


def get_gmail_service(log_level=logging.INFO):
    """Získá autorizovanou Gmail API službu, včetně přihlášení a uložení tokenu.
    Nejprve zkusí použít environmentální proměnné, pokud jsou dostupné.
    """
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    creds = None
    script_dir = Path(__file__).parent
    token_path = script_dir / "token.json"
    client_secrets_files = list(script_dir.glob("client_secret_*.json"))

    # --- 1. Pokus o inicializaci z environmentálních proměnných ---
    env_refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    env_access_token = os.getenv("GOOGLE_ACCESS_TOKEN")
    env_client_id = os.getenv("GOOGLE_CLIENT_ID")
    env_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    env_token_uri = os.getenv("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token")

    if env_refresh_token and env_client_id and env_client_secret:
        logging.info("Používám Gmail OAuth tokeny z environmentálních proměnných.")
        creds = Credentials(
            token=env_access_token,
            refresh_token=env_refresh_token,
            token_uri=env_token_uri,
            client_id=env_client_id,
            client_secret=env_client_secret,
            scopes=SCOPES
        )
    # --- 2. Pokud nejsou env proměnné, pokračuj původní logikou ---
    elif token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = None
            # 1. Pokus načíst ze souboru (pomocí glob)
            if client_secrets_files:
                client_secrets_file_path = client_secrets_files[0]
                if len(client_secrets_files) > 1:
                    logging.warning(
                        "Nalezeno více 'client_secret_*.json' souborů. Používám první: %s",
                        client_secrets_file_path
                    )
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(client_secrets_file_path), SCOPES
                    )
                    logging.info("Úspěšně načteny credentials ze souboru: %s", client_secrets_file_path)
                except (json.JSONDecodeError, ValueError, OSError) as e:
                    logging.warning(
                        "Soubor credentials (%s) nalezen, ale nelze ho parsovat: %s. Zkouším proměnné prostředí.",
                        client_secrets_file_path, e
                    )
                    flow = None
                except Exception as e:
                    logging.warning(
                        "Nepodařilo se načíst credentials ze souboru %s: %s. Zkouším proměnné prostředí.",
                        client_secrets_file_path, e
                    )
                    flow = None
            else:
                logging.info(
                    "Žádný 'client_secret_*.json' soubor nenalezen v %s. Zkouším proměnné prostředí.",
                    script_dir
                )

            # 2. Pokud soubor selhal nebo neexistuje, zkusit proměnné prostředí
            if flow is None:
                client_id = os.getenv('GOOGLE_CLIENT_ID')
                client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

                if client_id and client_secret:
                    logging.info("Používám credentials z proměnných prostředí (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET).")
                    client_config = {
                        "installed": {
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://accounts.google.com/o/oauth2/token"
                        }
                    }
                    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                else:
                    logging.error(
                        "Credentials nenalezeny ani v souboru (vzor 'client_secret_*.json') ani v proměnných prostředí (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)."
                    )
                    raise ValueError(
                        "Chybí konfigurace OAuth 2.0. Vytvořte 'client_secret_*.json' soubor nebo nastavte proměnné prostředí GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET."
                    )
            creds = flow.run_local_server(port=8080, open_browser=False)
        # Uložit token pouze pokud nebyl použit env
        if not (env_refresh_token and env_client_id and env_client_secret):
            with open(token_path, "w") as token:
                token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    return service

class GetCredentialsException(Exception):
    """Error raised when an error occurred while retrieving credentials.

    Attributes:
      authorization_url: Authorization URL to redirect the user to in order to
                         request offline access.
    """
    def __init__(self, authorization_url):
        """Construct a GetCredentialsException."""
        super().__init__(f"Authorization URL: {authorization_url}")
        self.authorization_url = authorization_url

class CodeExchangeException(GetCredentialsException):
    """Error raised when a code exchange has failed."""
    pass

class NoRefreshTokenException(GetCredentialsException):
    """Error raised when no refresh token has been found."""
    pass

class NoUserIdException(Exception):
    """Error raised when no user ID could be retrieved."""
    pass

def get_stored_credentials(user_id):
    """Retrieved stored credentials for the provided user ID.

    Args:
      user_id: User's ID.

    Returns:
      Stored oauth2client.client.OAuth2Credentials if found, None otherwise.

    Raises:
      NotImplementedError: This function has not been implemented.
    """
    # ... (Implementace databáze) ...
    raise NotImplementedError()

def store_credentials(user_id, credentials):
    """Store OAuth 2.0 credentials in the application's database.

    Args:
      user_id: User's ID.
      credentials: OAuth 2.0 credentials to store.

    Raises:
      NotImplementedError: This function has not been implemented.
    """
    # ... (Implementace databáze) ...
    raise NotImplementedError()

def exchange_code(authorization_code):
    """Exchange an authorization code for OAuth 2.0 credentials.
    
    Poznámka: Tato funkce stále používá CLIENTSECRETS_LOCATION definované nahoře.
    """
    flow = flow_from_clientsecrets(CLIENTSECRETS_LOCATION, ' '.join(SCOPES))
    flow.redirect_uri = REDIRECT_URI
    try:
        credentials = flow.step2_exchange(authorization_code)
        return credentials
    except FlowExchangeError as error:
        logging.error('An error occurred: %s', error)
        raise CodeExchangeException(None)

def get_user_info(credentials):
    """Send a request to the UserInfo API to retrieve the user's information.

    Args:
      credentials: oauth2client.client.OAuth2Credentials instance to authorize the
                   request.

    Returns:
      User information as a dict.
    """
    user_info_service = build(
        serviceName='oauth2', version='v2',
        http=credentials.authorize(httplib2.Http()))
    user_info = None
    try:
        user_info = user_info_service.userinfo().get().execute()
    except google_api_errors.HttpError as e:
        logging.error('An error occurred: %s', e)
    if user_info and user_info.get('id'):
        return user_info
    else:
        raise NoUserIdException()

def get_authorization_url(email_address, state):
    """Retrieve the authorization URL.

    Poznámka: Tato funkce stále používá CLIENTSECRETS_LOCATION definované nahoře.
    """
    flow = flow_from_clientsecrets(CLIENTSECRETS_LOCATION, ' '.join(SCOPES))
    flow.params['access_type'] = 'offline'
    flow.params['approval_prompt'] = 'force'
    flow.params['user_id'] = email_address
    flow.params['state'] = state
    # The step1_get_authorize_url method uses the flow.redirect_uri attribute.
    flow.redirect_uri = REDIRECT_URI
    return flow.step1_get_authorize_url()

def get_credentials(authorization_code, state):
    """Retrieve credentials using the provided authorization code.
    ...
    """
    email_address = ''
    try:
        credentials = exchange_code(authorization_code)
        user_info = get_user_info(credentials) # Can raise NoUserIdException or google_api_errors.HttpError
        email_address = user_info.get('email')
        user_id = user_info.get('id')
        if credentials.refresh_token is not None:
            store_credentials(user_id, credentials)
            return credentials
        else:
            credentials = get_stored_credentials(user_id)
            if credentials and credentials.refresh_token is not None:
                return credentials
    except CodeExchangeException as error:
        logging.error('An error occurred during code exchange.')
        # Drive apps should try to retrieve the user and credentials for the current
        # session.
        # If none is available, redirect the user to the authorization URL.
        error.authorization_url = get_authorization_url(email_address, state)
        raise error
    except NoUserIdException:
        logging.error('No user ID could be retrieved.')
    # No refresh token has been retrieved.
    authorization_url = get_authorization_url(email_address, state)
    raise NoRefreshTokenException(authorization_url)