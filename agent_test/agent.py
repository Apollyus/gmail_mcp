import asyncio

from anyio import Path
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient
import dotenv
import os

dotenv.load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Load Google credentials from environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_CREDENTIALS_NAME = os.getenv("GOOGLE_CREDENTIALS_NAME", "client_secret.json")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
GOOGLE_ACCESS_TOKEN = os.getenv("GOOGLE_ACCESS_TOKEN")

# Cesta k projektu
PROJECT_ROOT = Path(__file__).parent.parent
GMAIL_MCP_PATH = str(PROJECT_ROOT / "gmail_mcp.py")

async def main():
    # 1. LLM přes OpenRouter - jednotný přístup k různým modelům. Používají OpenAI SDK, takže je to kompatibilní s LangChain
    llm = ChatOpenAI(
        model="anthropic/claude-haiku-4.5",
        openai_api_base="https://openrouter.ai/api/v1",
        openai_api_key=OPENROUTER_API_KEY,
        temperature=0,
    )

    # 2. Konfigurace MCP serverů (nástrojů), může jich být mnohem více
    # Používáme Gmail MCP server přes fastmcp
    config = {
        "mcpServers": {
            "gmail": {
                "command": "python3",
                "args": [
                    GMAIL_MCP_PATH
                ], 
                "env": {
                    "GOOGLE_CLIENT_ID_env": GOOGLE_CLIENT_ID,
                    "GOOGLE_CLIENT_SECRET_env": GOOGLE_CLIENT_SECRET
                }
            }
        }
    }

    # 3. Inicializace MCP klienta přes knihovnu mcp_use
    client = MCPClient.from_dict(config)

    # Vytvoření MCP agenta s LLM a klientem
    # Tady je vlastně celý kouzelný kousek, který umožňuje LLM volat nástroje přes MCP
    agent = MCPAgent(llm=llm, client=client, max_steps=30)

    # 4. Spuštění dotazu
    result = await agent.run("""
Použij nástroj send_mail a odešli formální email v češtině na adresu: moraxcz@seznam.cz

Obsah emailu:
- Pozvi kolegu na schůzku ohledně nového projektu "AI Asistent"
- Datum: Středa 20. listopadu 2025
- Čas: 14:00
- Místo: Zasedací místnost 3.02, budova A

Email musí být formální a profesionální. Použij send_mail tool hned teď.
""")
    print("\n=== Výsledek ===")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
