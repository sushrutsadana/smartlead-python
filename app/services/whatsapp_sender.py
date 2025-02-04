from twilio.rest import Client
import logging
from typing import Dict, Optional
from ..config import settings

logger = logging.getLogger(__name__)

class WhatsAppSender:
    def __init__(self):
        try:
            # Initialize with exact credentials
            self.account_sid = settings.TWILIO_ACCOUNT_SID
            self.auth_token = settings.TWILIO_AUTH_TOKEN
            self.client = Client(self.account_sid, self.auth_token)
            self.sandbox_number = '+14155238886'  # Hardcode sandbox number
            logger.info("WhatsAppSender initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WhatsAppSender: {str(e)}")
            raise

    async def send_message(
        self,
        to_number: str,
        message: str
    ) -> Dict:
        """Simple WhatsApp message sender"""
        try:
            # Format exactly like the working code
            message = self.client.messages.create(
                from_=f'whatsapp:{self.sandbox_number}',
                body=message,
                to=to_number  # Expect full number with whatsapp: prefix
            )
            
            logger.info(f"Message sent with SID: {message.sid}")
            return {
                "status": "success",
                "message_sid": message.sid
            }
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            raise