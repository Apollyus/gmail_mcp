from fastmcp import FastMCP
from gmail_client import get_last_messages, send_mail, get_message_detail, get_messages_from_sender

mcp = FastMCP("Gmail MCP")

@mcp.tool
def list_emails(
    n: int = 5,
    status: str = "all",
    after: str = None,
    before: str = None
) -> str:
    """
    Vrátí seznam posledních n e-mailů z Gmail schránky uživatele.
    Vstup:
        n (int, volitelné) – počet e-mailů (výchozí 5)
        status (str, volitelné) – 'unread', 'read', 'all' (výchozí 'all')
        after (str, volitelné) – datum ve formátu 'YYYY/MM/DD' (zprávy po tomto datu)
        before (str, volitelné) – datum ve formátu 'YYYY/MM/DD' (zprávy před tímto datem)
    Výstup: Textový seznam e-mailů, každý na novém řádku, obsahující předmět zprávy.
    Pokud nejsou nalezeny žádné zprávy, vrátí 'No messages found.'.
    """
    messages = get_last_messages(n, status=status, after=after, before=before)
    if not messages:
        return "No messages found."
    output = "Last emails:\n"
    for msg in messages:
        output += f"- {msg['subject']}\n"
    return output

@mcp.tool
def list_emails_from_sender(
    sender_email: str,
    n: int = 5,
    after: str = None,
    before: str = None
) -> str:
    """
    Vrátí posledních n e-mailů od zadaného odesílatele.
    Vstup:
        sender_email (str) – e-mailová adresa odesílatele,
        n (int, volitelné) – počet e-mailů (výchozí 5),
        after (str, volitelné) – datum ve formátu 'YYYY/MM/DD' (zprávy po tomto datu),
        before (str, volitelné) – datum ve formátu 'YYYY/MM/DD' (zprávy před tímto datem)
    Výstup: Textový seznam e-mailů, každý na novém řádku, obsahující předmět zprávy.
    Pokud nejsou nalezeny žádné zprávy, vrátí 'No messages found.'.
    """
    messages = get_messages_from_sender(sender_email, n=n, after=after, before=before)
    if not messages:
        return "No messages found."
    output = f"Last emails from {sender_email}:\n"
    for msg in messages:
        output += f"- {msg['subject']}\n"
    return output

@mcp.tool
def get_email_detail(message_id: str) -> str:
    """
    Získá detail konkrétního e-mailu podle jeho ID.
    Vstup: message_id (str) – ID zprávy.
    Výstup: Textový obsah e-mailu včetně předmětu a těla zprávy.
    Pokud zpráva není nalezena, vrátí 'Message not found.'.
    """
    msg_detail = get_message_detail(message_id)
    if not msg_detail:
        return "Message not found."
    headers = msg_detail.get("payload", {}).get("headers", [])
    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(no subject)")
    body = ""
    parts = msg_detail.get("payload", {}).get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain":
            body_data = part.get("body", {}).get("data", "")
            body += body_data.encode('utf-8').decode('utf-8')
    return f"Subject: {subject}\n\n{body}"

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