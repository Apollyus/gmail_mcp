#!/usr/bin/env python3
from pathlib import Path
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose'
]

def generate_token():
    script_dir = Path(__file__).parent
    token_path = script_dir / "token.json"
    client_secrets_files = list(script_dir.glob("client_secret_*.json"))
    
    if not client_secrets_files:
        print("❌ Nenalezen žádný client_secret_*.json soubor!")
        return
    
    client_secrets_file = client_secrets_files[0]
    print(f"✓ Používám credentials soubor: {client_secrets_file.name}")
    
    creds = None
    
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("⟳ Token expiroval, obnovuji...")
            creds.refresh(Request())
        else:
            print("🌐 Spouštím OAuth flow...")
            
            # Načtení konfigurace
            with open(client_secrets_file, 'r') as f:
                client_config = json.load(f)

            # Fix pro "web" vs "installed" typ aplikace
            if 'web' in client_config:
                config = {
                    'installed': {
                        'client_id': client_config['web']['client_id'],
                        'client_secret': client_config['web']['client_secret'],
                        'auth_uri': client_config['web']['auth_uri'],
                        'token_uri': client_config['web']['token_uri'],
                        'redirect_uris': ['http://localhost:8080/']
                    }
                }
                flow = InstalledAppFlow.from_client_config(config, SCOPES)
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_file), SCOPES)

            # Tady je ta změna - jednoduché spuštění bez vláken
            creds = flow.run_local_server(
                port=8080,
                prompt='consent',
                authorization_prompt_message='Otevírám prohlížeč. Prosím autorizujte aplikaci.',
                success_message='Autorizace úspěšná! Můžete zavřít toto okno a vrátit se do terminálu.',
                open_browser=True
            )
            
        with open(token_path, "w") as token:
            token.write(creds.to_json())
        print(f"✅ Token uložen do: {token_path}")

if __name__ == "__main__":
    generate_token()