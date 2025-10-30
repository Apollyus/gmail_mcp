from fastmcp import FastMCP
from gmail_client import get_last_messages, send_mail

mcp = FastMCP("Gmail MCP")

@mcp.tool
def greet(name: str) -> str:
    """
    Pozdraví uživatele zadaným jménem.
    Vstup: name (str) – jméno osoby, kterou chcete pozdravit.
    Výstup: Textový pozdrav ve formátu "Hello, {name}!".
    """
    return f"Hello, {name}!"

@mcp.tool
def list_emails(n: int = 5) -> str:
    """
    Vrátí seznam posledních n e-mailů z Gmail schránky uživatele.
    Vstup: n (int, volitelné) – počet e-mailů, které chcete zobrazit (výchozí je 5).
    Výstup: Textový seznam e-mailů, každý na novém řádku, obsahující krátký výňatek (snippet) zprávy.
    Pokud nejsou nalezeny žádné zprávy, vrátí 'No messages found.'.
    """
    messages = get_last_messages(n)
    if not messages:
        return "No messages found."
    output = "Last emails:\n"
    for msg in messages:
        output += f"- {msg['snippet']}\n"
    return output

@mcp.tool
def send_mail(recipient: str, subject: str, body: str) -> str:
    """
    Odešle e-mail na zadanou adresu.
    Vstup:
        recipient (str) – e-mailová adresa příjemce,
        subject (str) – předmět zprávy,
        body (str) – text zprávy.
    Výstup: Potvrzení o odeslání e-mailu s uvedením adresy a předmětu.
    """
    send_mail(subject, body, recipient)
    return f"Email sent to {recipient} with subject '{subject}'."

if __name__ == "__main__":
    mcp.run()