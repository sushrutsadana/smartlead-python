from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import logging
from typing import Optional
from ..config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        try:
            self.gmail_user = settings.GMAIL_USER
            # Use all authorized scopes
            SCOPES = [
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.compose',
                'https://www.googleapis.com/auth/gmail.modify'
            ]
            
            credentials = Credentials.from_authorized_user_info({
                'client_id': settings.GMAIL_CLIENT_ID,
                'client_secret': settings.GMAIL_CLIENT_SECRET,
                'refresh_token': settings.GMAIL_REFRESH_TOKEN
            }, SCOPES)
            
            self.gmail = build('gmail', 'v1', credentials=credentials, cache_discovery=False)
            logger.info("EmailService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize EmailService: {str(e)}")
            raise

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> dict:
        """
        Send an email to a lead
        
        Args:
            to_email: Recipient's email address
            subject: Email subject
            body: Email body (plain text)
            cc: Optional CC recipients
            bcc: Optional BCC recipients
            
        Returns:
            dict: Response from Gmail API
        """
        try:
            # Create message
            message = MIMEText(body)
            message['to'] = to_email
            message['from'] = self.gmail_user
            message['subject'] = subject
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc

            # Encode the message
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            # Send the email
            try:
                sent_message = self.gmail.users().messages().send(
                    userId='me',  # Changed from self.gmail_user to 'me'
                    body={'raw': encoded_message}
                ).execute()
                
                logger.info(f"Email sent successfully to {to_email}")
                return {
                    "status": "success",
                    "message_id": sent_message['id'],
                    "thread_id": sent_message.get('threadId')
                }
            except Exception as e:
                logger.error(f"Gmail API error: {str(e)}")
                raise

        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            raise 