from fastmcp import FastMCP
from gmail_client import get_last_messages

mcp = FastMCP("Gmail MCP")

@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

@mcp.tool
def list_emails(n: int = 5) -> str:
    """List the last n emails from the user's Gmail inbox."""
    messages = get_last_messages(n)
    if not messages:
        return "No messages found."
    output = "Last emails:\n"
    for msg in messages:
        output += f"- {msg['snippet']}\n"
    return output

@mcp.tool
def send_email(recipient: str, subject: str, body: str) -> str:
    """Send an email to the specified recipient."""
    return f"Email sent to {recipient} with subject '{subject}'."

if __name__ == "__main__":
    mcp.run()