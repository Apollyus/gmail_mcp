import asyncio

from anyio import Path
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient
import dotenv
import os

dotenv.load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


# Cesta k projektu
PROJECT_ROOT = Path(__file__).parent.parent.parent
GMAIL_MCP_PATH = str(PROJECT_ROOT / "src" / "gmail-mcp" / "gmail_mcp.py")

async def main():
    # 1. LLM přes OpenRouter - jednotný přístup k různým modelům. Používají OpenAI SDK, takže je to kompatibilní s LangChain
    llm = ChatOpenAI(
        model="google/gemini-2.5-flash-lite-preview-09-2025",
        openai_api_base="https://openrouter.ai/api/v1",
        openai_api_key=OPENROUTER_API_KEY,
        temperature=0,
    )

    # 2. Konfigurace MCP serverů (nástrojů), může jich být mnohem více
    # Používáme oficiální Notion MCP server přes mcp.notion.com
    config = {
        
                "gmail": {
                    "command": "uv",
                    "args": [
                        "run",
                        "--with",
                        "fastmcp",
                        "fastmcp",
                        "run",
                        GMAIL_MCP_PATH
                    ], 
                    "env": {
                        "GOOGLE_REFRESH_TOKEN": f"${{GOOGLE_REFRESH_TOKEN}}",
                        "GOOGLE_ACCESS_TOKEN": f"${{GOOGLE_ACCESS_TOKEN}}",
                        "GOOGLE_CLIENT_ID": f"${{GOOGLE_CLIENT_ID}}",
                        "GOOGLE_CLIENT_SECRET": f"${{GOOGLE_CLIENT_SECRET}}"
                    }
                }
    }

    # 3. Inicializace MCP klienta přes knihovnu mcp_use
    client = MCPClient.from_dict(config)

    # Vytvoření MCP agenta s LLM a klientem
    # Tady je vlastně celý kouzelný kousek, který umožňuje LLM volat nástroje přes MCP
    agent = MCPAgent(llm=llm, client=client, max_steps=30)

    # 4. Spuštění dotazu
    result = await agent.run("Napiš mi e-mail v češtině, kterým pozveš kolegu na schůzku ohledně nového projektu na příští týden. Ujisti se, že e-mail je formální a obsahuje datum, čas a místo schůzky. Odesílatel bude gmailová adresa faltynekvojtech@gmail.com")
    print("\n=== Výsledek ===")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
