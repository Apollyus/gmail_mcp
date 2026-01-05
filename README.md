# Gmail MCP Server

**MCP (Model Context Protocol) server pro Gmail**, který umožňuje AI asistentům číst, vyhledávat a odesílat e-maily přímo z tvého Gmail účtu.

---

## Co je MCP?

**Model Context Protocol** je otevřený standard od Anthropicu, který definuje, jak mohou AI modely komunikovat s externími nástroji. Můžeme si ho představit jako USB pro AI – jednotné rozhraní, přes které může jakýkoliv AI model používat jakékoliv nástroje.

Tento projekt implementuje MCP server, který AI asistentům zpřístupňuje Gmail API. Agent pak může:
- Přečíst poslední e-maily
- Vyhledat zprávy podle odesílatele, předmětu nebo obsahu
- Odeslat e-mail na zadanou adresu

---

## Architektura projektu

```
┌─────────────────────────────────────────────────────────────────┐
│                         AI Agent                                │
│  (Claude, GPT, lokální model přes LangChain + OpenRouter)       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ MCP protokol (JSON-RPC přes stdio)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      gmail_mcp.py                               │
│  FastMCP server - definuje nástroje, které AI může používat     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ volání Python funkcí
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     gmail_client.py                             │
│  Wrapper nad Gmail API - samotná logika práce s e-maily         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      gmail_auth.py                              │
│  OAuth 2.0 autentizace - získání a obnova tokenů                │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Gmail API                                 │
│  (Google servery)                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Popis souborů

### `gmail_mcp.py` — MCP Server

Srdce celého projektu. Používá knihovnu **FastMCP** pro vytvoření MCP serveru.

```python
from fastmcp import FastMCP
mcp = FastMCP("Gmail MCP")

@mcp.tool
def list_emails(n: int = 5, status: str = "all") -> str:
    """AI tuto funkci zavolá, když chce seznam e-mailů."""
    ...
```

**Vystavené nástroje:**

| Nástroj | Popis |
|---------|-------|
| `list_emails` | Vrátí posledních N e-mailů (filtr: přečtené/nepřečtené, datum) |
| `list_emails_from_sender` | E-maily od konkrétního odesílatele |
| `list_emails_by_subject` | E-maily podle textu v předmětu |
| `list_emails_by_body` | E-maily podle textu v těle zprávy |
| `get_email_detail` | Detaily konkrétního e-mailu podle ID |
| `send_mail` | Odešle e-mail |

Každý nástroj má detailní docstring, který AI model používá k pochopení, kdy a jak nástroj použít.

---

### `gmail_client.py` — Gmail API Wrapper

Obsahuje funkce, které skutečně komunikují s Gmail API. MCP server je pouze „obálka", která tyto funkce vystavuje ven.

**Klíčové funkce:**

```python
def get_last_messages(n=5, status="all", after=None, before=None):
    """
    Vrátí posledních N zpráv jako seznam slovníků.
    Podporuje filtrování podle stavu (read/unread) a data.
    """

def send_mail(subject, message_text, to):
    """
    Odešle e-mail přes Gmail API.
    Zpráva se kóduje do MIME formátu a posílá jako base64.
    """

def get_messages_from_sender(sender_email, n=100):
    """
    Vyhledá zprávy od konkrétního odesílatele pomocí Gmail query syntaxe.
    Interně volá: q='from:email@example.com'
    """
```

Funkce využívají Gmail API query syntaxi – stejnou, jakou bys psal do vyhledávacího pole v Gmailu (`is:unread`, `from:someone@email.com`, `after:2025/01/01`).

---

### `gmail_auth.py` — OAuth 2.0 Autentizace

Nejkomplexnější soubor. Řeší přihlášení ke Google účtu přes OAuth 2.0.

**Jak autentizace funguje:**

1. **Kontrola ENV proměnných** – Pokud jsou nastavené `GOOGLE_CLIENT_ID_env`, `GOOGLE_CLIENT_SECRET_env` a `GOOGLE_REFRESH_TOKEN_env`, použijí se přímo
2. **Kontrola `token.json`** – Existující uložený token z předchozího přihlášení
3. **Refresh tokenu** – Pokud token expiroval, automaticky se obnoví
4. **Manuální OAuth flow** – Fallback pro první přihlášení (zobrazí URL, uživatel se přihlásí a vloží odpověď)

```python
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',   # čtení e-mailů
    'https://www.googleapis.com/auth/gmail.send',       # odesílání
    'https://www.googleapis.com/auth/gmail.compose'     # vytváření konceptů
]
```

Token se ukládá do `token.json` a automaticky se obnovuje, takže opakované přihlašování není nutné.

---

### `agent_test/agent.py` — Ukázkový AI Agent

Demonstruje, jak propojit MCP server s AI modelem pomocí knihoven **LangChain** a **mcp_use**.

```python
# Konfigurace LLM (Claude přes OpenRouter)
llm = ChatOpenAI(
    model="anthropic/claude-haiku-4.5",
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=OPENROUTER_API_KEY,
)

# Konfigurace MCP serveru
config = {
    "mcpServers": {
        "gmail": {
            "command": VENV_PYTHON,
            "args": [GMAIL_MCP_PATH],
            "env": {...}  # credentials
        }
    }
}

# Propojení
client = MCPClient.from_dict(config)
agent = MCPAgent(llm=llm, client=client, max_steps=30)

# Spuštění
result = await agent.run("Pošli email na adresu...")
```

Agent automaticky:
1. Spustí Gmail MCP server jako subprocess
2. Načte dostupné nástroje
3. Pošle prompt do LLM
4. LLM se rozhodne, které nástroje použít
5. Agent nástroje zavolá a vrátí výsledek

---

### `generate_token.py` — Pomocný skript

Jednoduchý skript pro vygenerování `token.json`. Užitečný pro první nastavení.

```bash
python generate_token.py
# → Otevře prohlížeč, přihlásíš se, token se uloží
```

---

### `test_gmail.py` — Diagnostický skript

Ověří, že vše funguje:
- Kontrola `client_secret_*.json`
- Kontrola nainstalovaných závislostí
- Test připojení k Gmail API

---

## Instalace a spuštění

### 1. Klonování a závislosti

```bash
git clone <repo>
cd gmail_mcp
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Google Cloud Console

1. Jdi na [Google Cloud Console](https://console.cloud.google.com/)
2. Vytvoř nový projekt
3. Povol **Gmail API**
4. Vytvoř OAuth 2.0 credentials (typ: Desktop application)
5. Stáhni JSON a přejmenuj na `client_secret_xxx.json`

### 3. Přihlášení

```bash
python generate_token.py
```

### 4. Environment variables

Vytvoř `.env` soubor:

```env
OPENROUTER_API_KEY=sk-or-v1-xxx
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxx
GOOGLE_REFRESH_TOKEN=1//xxx
```

### 5. Spuštění agenta

```bash
.\venv\Scripts\python.exe .\agent_test\agent.py
```

---

## Použití jako MCP server (Claude Desktop)

Přidej do `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gmail": {
      "command": "C:/cesta/k/venv/Scripts/python.exe",
      "args": ["C:/cesta/k/gmail_mcp.py"],
      "env": {
        "GOOGLE_REFRESH_TOKEN_env": "...",
        "GOOGLE_CLIENT_ID_env": "...",
        "GOOGLE_CLIENT_SECRET_env": "..."
      }
    }
  }
}
```

---

## Technologie

- **Python 3.12+**
- **FastMCP** – knihovna pro snadné vytváření MCP serverů
- **Google API Python Client** – oficiální klient pro Gmail API
- **LangChain** – framework pro AI agenty
- **mcp_use** – knihovna pro propojení MCP s LangChain
- **OpenRouter** – jednotný přístup k různým LLM modelům

---

## Licence

MIT

---

## Autor

Projekt vytvořen jako ukázka integrace AI s reálnými službami pomocí MCP protokolu.

## Zdroje
- https://medium.com/@doogwoo/connecting-claude-mcp-using-fastmcp-a8f2ee602c66