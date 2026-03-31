import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
from typing import List, Dict
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# CentraleSupelec Server Configurations
IMAP_SERVER = "mailhost1-saclay.centralesupelec.fr"
IMAP_PORT = 993
SMTP_SERVER = "smtp.centralesupelec.fr"
SMTP_PORT = 587

def get_credentials():
    email_addr = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    if not email_addr or not password:
        raise ValueError("EMAIL_ADDRESS or EMAIL_PASSWORD not found in .env")
    return email_addr, password

def _clean_html(html_content: str) -> str:
    """Removes HTML tags from email bodies to make them readable for the agent."""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator='\n', strip=True)

class EmailManager:
    @staticmethod
    def _fetch_and_parse_emails(mail, email_ids: list) -> str:
        """Helper function to fetch and parse a list of email IDs."""
        results = []
        for e_id in reversed(email_ids): # Newest first
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decode Subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8", errors="ignore")
                        
                    # Decode Sender
                    from_ = msg.get("From")
                    date_ = msg.get("Date")
                    
                    # Extract Body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            content_disposition = str(part.get("Content-Disposition"))
                            
                            if content_type == "text/plain" and "attachment" not in content_disposition:
                                try:
                                    body = part.get_payload(decode=True).decode(part.get_content_charset("utf-8") or "utf-8", errors="ignore")
                                    break # Prefer plain text
                                except:
                                    pass
                            elif content_type == "text/html" and "attachment" not in content_disposition:
                                try:
                                    html_body = part.get_payload(decode=True).decode(part.get_content_charset("utf-8") or "utf-8", errors="ignore")
                                    body = _clean_html(html_body)
                                except:
                                    pass
                    else:
                        try:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                charset = msg.get_content_charset("utf-8") or "utf-8"
                                body = payload.decode(charset, errors="ignore")
                                if msg.get_content_type() == "text/html":
                                    body = _clean_html(body)
                        except:
                            body = "Could not decode body."
                            
                    results.append(f"Date: {date_}\nFrom: {from_}\nSubject: {subject}\nBody:\n{body[:1500]}...\n")
        
        return "\n\n--- NEXT EMAIL ---\n\n".join(results)

    @staticmethod
    def read_latest_emails(count: int = 5) -> str:
        """
        Connects to the CentraleSupelec IMAP server and retrieves the latest unread emails.
        """
        try:
            email_addr, password = get_credentials()
            
            mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
            mail.login(email_addr, password)
            mail.select("inbox")
            
            status, messages = mail.search(None, "UNREAD")
            if status != "OK" or not messages[0]:
                mail.logout()
                return "You have no new unread emails in your PhD inbox."
                
            email_ids = messages[0].split()
            latest_email_ids = email_ids[-count:]
            
            result = EmailManager._fetch_and_parse_emails(mail, latest_email_ids)
            mail.logout()
            return result
            
        except Exception as e:
            logger.error(f"Failed to read emails: {e}")
            return f"Error reading emails: {str(e)}"

    @staticmethod
    def search_emails(search_criteria: str, count: int = 5) -> str:
        """
        Searches the CentraleSupelec IMAP server for specific emails.
        
        Args:
            search_criteria: IMAP search string (e.g., 'FROM "professor@domain.com"', 'SUBJECT "Thesis"', 'BODY "FORVIA"').
        """
        try:
            email_addr, password = get_credentials()
            
            mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
            mail.login(email_addr, password)
            mail.select("inbox")
            
            # Use ALL so it doesn't just look at unread emails
            status, messages = mail.search(None, search_criteria)
            if status != "OK" or not messages[0]:
                mail.logout()
                return f"No emails found matching criteria: {search_criteria}"
                
            email_ids = messages[0].split()
            latest_email_ids = email_ids[-count:]
            
            result = EmailManager._fetch_and_parse_emails(mail, latest_email_ids)
            mail.logout()
            return result
            
        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            return f"Error searching emails: {str(e)}"

    @staticmethod
    def send_email(to_address: str, subject: str, body: str) -> str:
        """
        Connects to the CentraleSupelec SMTP server and sends an email.
        """
        try:
            email_addr, password = get_credentials()
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_addr
            msg['To'] = to_address
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Connect to SMTP (STARTTLS)
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls() # Secure the connection
            server.login(email_addr, password)
            server.send_message(msg)
            server.quit()
            
            return f"Successfully sent email to {to_address} with subject '{subject}'."
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return f"Error sending email: {str(e)}"

email_manager = EmailManager()
