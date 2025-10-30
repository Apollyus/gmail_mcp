"""
Jednoduchý test Gmail autentizace
"""
import os
from pathlib import Path

# Najít cestu k client_secret souboru
script_dir = Path(__file__).parent
client_secrets = list(script_dir.glob("client_secret_*.json"))

if client_secrets:
    print(f"✓ Nalezen credentials soubor: {client_secrets[0].name}")
    
    # Zkontrolovat, jestli je soubor validní JSON
    import json
    try:
        with open(client_secrets[0], 'r') as f:
            data = json.load(f)
            print(f"✓ JSON soubor je validní")
            
            # Zobrazit typ credentials
            if 'web' in data:
                print(f"✓ Typ: Web application")
                print(f"  Client ID: {data['web'].get('client_id', 'N/A')[:50]}...")
            elif 'installed' in data:
                print(f"✓ Typ: Installed application")
                print(f"  Client ID: {data['installed'].get('client_id', 'N/A')[:50]}...")
            else:
                print(f"⚠ Neznámý typ credentials")
                
    except json.JSONDecodeError as e:
        print(f"✗ Chyba při parsování JSON: {e}")
else:
    print("✗ Client secret soubor nenalezen!")
    print("  Ujistěte se, že máte client_secret_*.json soubor v projektu")

print("\n--- Kontrola závislostí ---")
required_packages = [
    'google-auth',
    'google-auth-oauthlib', 
    'google-auth-httplib2',
    'google-api-python-client'
]

for package in required_packages:
    try:
        __import__(package.replace('-', '_'))
        print(f"✓ {package}")
    except ImportError:
        print(f"✗ {package} - CHYBÍ (nainstalujte: pip install {package})")


# --- Ukázka: Připojení k Gmail API a načtení posledních e-mailů ---
print("\n--- Připojení k Gmail API ---")
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    import base64
    import email
    from google.auth.transport.requests import Request
except ImportError as e:
    print(f"Chybí knihovna: {e}")
    exit(1)

# Scopes pro čtení e-mailů
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def get_gmail_service():
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
    print("✓ Připojeno k Gmail API")
    # Načíst posledních 5 zpráv
    results = service.users().messages().list(userId="me", maxResults=5).execute()
    messages = results.get("messages", [])
    if not messages:
        print("Žádné zprávy nenalezeny.")
    else:
        print("Poslední zprávy:")
        for msg in messages:
            msg_detail = service.users().messages().get(userId="me", id=msg["id"]).execute()
            headers = msg_detail.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(bez předmětu)")
            print(f"- ID: {msg['id']} | Předmět: {subject}")
except Exception as e:
    print(f"Chyba při práci s Gmail API: {e}")
