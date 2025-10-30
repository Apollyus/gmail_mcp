import base64
from email.mime.text import MIMEText
import logging
from gmail_auth import get_gmail_service
from googleapiclient.errors import HttpError

def log(msg, level=logging.INFO):
    logging.log(level, msg)

def ListMessages(service, user, query='', log_level=logging.INFO):
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
                        response = service.users().messages().list(userId=user, q=query, pageToken=page_token).execute()
                        if 'messages' in response:
                                messages.extend(response['messages'])

                return messages
        except HttpError as error:
            log(f'An error occurred: {error}', logging.ERROR)
            if error.resp.status == 401:
                # Credentials have been revoked.
                # TODO: Redirect the user to the authorization URL.
                raise NotImplementedError()

def get_last_messages(n=5, log_level=logging.INFO):
    """Vrátí posledních n zpráv jako seznam slovníků s ID a předmětem."""
    try:
        service = get_gmail_service(log_level)
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
    except HttpError as error:
        log(f'Chyba při načítání zpráv: {error}', logging.ERROR)
        return []
    
def get_message_detail(message_id, log_level=logging.INFO):
    """Získá detail konkrétního e-mailu podle jeho ID.
    Args:
        message_id: ID zprávy
    Returns:
        Slovník s detaily zprávy nebo None při chybě
    """
    try:
        service = get_gmail_service(log_level)
        msg_detail = service.users().messages().get(userId="me", id=message_id, format="full").execute()
        log(f"Načteny detaily zprávy ID: {message_id}", log_level)
        return msg_detail
    except HttpError as error:
        log(f'Chyba při načítání detailu zprávy: {error}', logging.ERROR)
        return None

def send_mail(subject, message_text, to, log_level=logging.INFO):
    """Odešle email přes Gmail API z účtu přihlášeného uživatele.
    Args:
        subject: Předmět zprávy
        message_text: Text zprávy
        to: Emailová adresa příjemce
    Returns:
        ID odeslané zprávy nebo None při chybě
    """
    try:
        service = get_gmail_service(log_level)
        mime_message = MIMEText(message_text)
        mime_message['to'] = to
        mime_message['from'] = 'me'
        mime_message['subject'] = subject
        raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
        body = {'raw': raw}
        sent_message = service.users().messages().send(userId="me", body=body).execute()
        log(f"Zpráva odeslána, ID: {sent_message['id']}")
        return sent_message['id']
    except HttpError as error:
        log(f'Chyba při odesílání zprávy: {error}', logging.ERROR)
        return None

def create_draft(subject, message_text, to, log_level=logging.INFO):
    """Vytvoří koncept e-mailu v Gmailu.
    Args:
        subject: Předmět zprávy
        message_text: Text zprávy
        to: Emailová adresa příjemce
    Returns:
        ID konceptu nebo None při chybě
    """
    try:
        service = get_gmail_service(log_level)
        mime_message = MIMEText(message_text)
        mime_message['to'] = to
        mime_message['from'] = 'me'
        mime_message['subject'] = subject
        raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
        body = {'message': {'raw': raw}}
        draft = service.users().drafts().create(userId="me", body=body).execute()
        log(f"Koncept vytvořen, ID: {draft['id']}")
        return draft['id']
    except HttpError as error:
        log(f'Chyba při vytváření konceptu: {error}', logging.ERROR)
        return None
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    last_messages = get_last_messages(3)
    for msg in last_messages:
        print(f"ID: {msg['id']}, Subject: {msg['subject']}")
    #send_mail("Test Subject", "This is a test message.", "moraxcz@seznam.cz")
    create_draft("Test Subject", "This is a test message.", "moraxcz@seznam.cz")