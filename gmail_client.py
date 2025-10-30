from googleapiclient.discovery import build
from googleapiclient import errors
import httplib2

import os
from pathlib import Path
import logging

# Nastavení logování
def setup_logging(level=logging.INFO):
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s')

# Najít cestu k client_secret souboru
script_dir = Path(__file__).parent
client_secrets = list(script_dir.glob("client_secret_*.json"))

def log(msg, level=logging.INFO):
    logging.log(level, msg)

setup_logging()

if client_secrets:
    log(f"✓ Nalezen credentials soubor: {client_secrets[0].name}")
    import json
    try:
        with open(client_secrets[0], 'r') as f:
            data = json.load(f)
            log(f"✓ JSON soubor je validní")
            if 'web' in data:
                log(f"✓ Typ: Web application")
                log(f"  Client ID: {data['web'].get('client_id', 'N/A')[:50]}...")
            elif 'installed' in data:
                log(f"✓ Typ: Installed application")
                log(f"  Client ID: {data['installed'].get('client_id', 'N/A')[:50]}...")
            else:
                log(f"⚠ Neznámý typ credentials", logging.WARNING)
    except json.JSONDecodeError as e:
        log(f"✗ Chyba při parsování JSON: {e}", logging.ERROR)
else:
    log("✗ Client secret soubor nenalezen!", logging.ERROR)
    log("  Ujistěte se, že máte client_secret_*.json soubor v projektu", logging.ERROR)

# Scopes pro čtení e-mailů
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/gmail.send"]

def get_gmail_service(log_level=logging.INFO):
    setup_logging(log_level)
    creds = None
    token_path = script_dir / "token.json"
    if token_path.exists():
        import json
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets[0]), SCOPES)
            creds = flow.run_local_server(port=8080)
        # Uložit token
        with open(token_path, "w") as token:
            token.write(creds.to_json())
    service = build("gmail", "v1", credentials=creds)
    return service

try:
    service = get_gmail_service()
    log("✓ Připojeno k Gmail API")
    # Načíst posledních 5 zpráv
    results = service.users().messages().list(userId="me", maxResults=5).execute()
    messages = results.get("messages", [])
    if not messages:
        log("Žádné zprávy nenalezeny.", logging.WARNING)
    else:
        log("Poslední zprávy:")
        for msg in messages:
            msg_detail = service.users().messages().get(userId="me", id=msg["id"]).execute()
            headers = msg_detail.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(bez předmětu)")
            log(f"- ID: {msg['id']} | Předmět: {subject}")
except Exception as e:
    log(f"Chyba při práci s Gmail API: {e}", logging.ERROR)

credentials = get_gmail_service()

def ListMessages(service, user, query='', log_level=logging.INFO):
        setup_logging(log_level)
        """Gets a list of messages.

        Args:
                service: Authorized Gmail API service instance.
                user: The email address of the account.
                query: String used to filter messages returned.
                log_level: Logging level

        Returns:
                List of messages that match the criteria of the query. Note that the
                returned list contains Message IDs, you must use get with the
                appropriate id to get the details of a Message.
        """
        try:
                response = service.users().messages().list(userId=user, q=query).execute()
                messages = []
                if 'messages' in response:
                        messages.extend(response['messages'])

                while 'nextPageToken' in response:
                        page_token = response['nextPageToken']
                        response = service.users().messages().list(userId=user, q=query,
                                                                                        pageToken=page_token).execute()
                        if 'messages' in response:
                                messages.extend(response['messages'])

                return messages
        except errors.HttpError as error:
                log(f'An error occurred: {error}', logging.ERROR)
                if error.resp.status == 401:
                        # Credentials have been revoked.
                        # TODO: Redirect the user to the authorization URL.
                        raise NotImplementedError()

def get_last_messages(service, n=5, log_level=logging.INFO):
    setup_logging(log_level)
    """Vrátí posledních n zpráv jako seznam slovníků s ID a předmětem."""
    try:
        results = service.users().messages().list(userId="me", maxResults=n).execute()
        messages = results.get("messages", [])
        output = []
        for msg in messages:
            msg_detail = service.users().messages().get(userId="me", id=msg["id"]).execute()
            headers = msg_detail.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(bez předmětu)")
            output.append({"id": msg["id"], "subject": subject})
        log(f"Načteno {len(output)} zpráv.", log_level)
        return output
    except errors.HttpError as error:
        log(f'Chyba při načítání zpráv: {error}', logging.ERROR)
        return []