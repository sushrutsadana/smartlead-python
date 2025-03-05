from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import logging
from typing import Optional, Dict
from ..config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self, supabase=None):
        self.supabase = supabase
        self.gmail_services = {}  # Cache of Gmail services by email
        
    async def get_gmail_service(self, email: str = None):
        """Get a Gmail service for the specified email or default"""
        try:
            # If email is not specified, use the default
            if not email:
                email = settings.GMAIL_USER
                
                # Use the credentials from environment variables
                credentials = Credentials.from_authorized_user_info({
                    'client_id': settings.GMAIL_CLIENT_ID,
                    'client_secret': settings.GMAIL_CLIENT_SECRET,
                    'refresh_token': settings.GMAIL_REFRESH_TOKEN
                }, ['https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/gmail.compose',
                    'https://www.googleapis.com/auth/gmail.modify'])
                
                service = build('gmail', 'v1', credentials=credentials, cache_discovery=False)
                return service, email
            
            # Check if we already have a service for this email
            if email in self.gmail_services:
                return self.gmail_services[email], email
            
            # If not, get credentials from Supabase
            if not self.supabase:
                raise ValueError("Supabase client is required to get credentials")
                
            result = self.supabase.table("gmail_credentials").select("*").eq("email", email).execute()
            
            if not result.data:
                raise ValueError(f"No Gmail credentials found for {email}")
                
            creds_data = result.data[0]
            
            # Create credentials
            credentials = Credentials(
                token=creds_data['access_token'],
                refresh_token=creds_data['refresh_token'],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=['https://www.googleapis.com/auth/gmail.send',
                       'https://www.googleapis.com/auth/gmail.compose',
                       'https://www.googleapis.com/auth/gmail.modify']
            )
            
            # Build the service
            service = build('gmail', 'v1', credentials=credentials, cache_discovery=False)
            
            # Cache it
            self.gmail_services[email] = service
            
            return service, email
            
        except Exception as e:
            logger.error(f"Error getting Gmail service: {str(e)}")
            raise

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        from_email: Optional[str] = None
    ) -> dict:
        """
        Send an email to a lead
        
        Args:
            to_email: Recipient's email address
            subject: Email subject
            body: Email body (plain text)
            cc: Optional CC recipients
            bcc: Optional BCC recipients
            from_email: Optional sender email (must be connected)
            
        Returns:
            dict: Response from Gmail API
        """
        try:
            # Get Gmail service for the specified email
            gmail, sender_email = await self.get_gmail_service(from_email)
            
            # Create message
            message = MIMEText(body)
            message['to'] = to_email
            message['from'] = sender_email
            message['subject'] = subject
            
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc

            # Encode the message
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            # Send the email
            try:
                sent_message = gmail.users().messages().send(
                    userId='me',
                    body={'raw': encoded_message}
                ).execute()
                
                logger.info(f"Email sent successfully to {to_email} from {sender_email}")
                return {
                    "status": "success",
                    "message_id": sent_message['id'],
                    "thread_id": sent_message.get('threadId'),
                    "from": sender_email
                }
            except Exception as e:
                logger.error(f"Gmail API error: {str(e)}")
                raise

        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            raise 