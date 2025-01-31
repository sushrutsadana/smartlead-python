from twilio.rest import Client
from twilio.request_validator import RequestValidator
import logging
from typing import Dict
from ..config import settings
import anthropic
from ..schemas.lead import LeadCreate
from .lead_service import LeadService

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = '+14155238886'
        self.webhook_url = settings.TWILIO_WEBHOOK_URL
        self.client = Client(self.account_sid, self.auth_token)
        self.claude = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.validator = RequestValidator(self.auth_token)
        logger.info(f"WhatsAppService initialized with webhook URL: {self.webhook_url}")

    async def handle_incoming_webhook(self, request_data: Dict) -> Dict:
        """Handle incoming WhatsApp message webhook from Twilio"""
        try:
            from_number = request_data.get('From', '').replace('whatsapp:', '')
            body = request_data.get('Body', '')
            
            logger.info(f"Received message from {from_number}: {body}")
            
            # Extract lead info using Claude
            lead_info = await self.extract_lead_info(body)
            logger.info(f"Extracted lead info: {lead_info}")
            
            # Create lead with available information
            lead_data = LeadCreate(
                first_name=lead_info.get('first_name', 'Unknown'),
                last_name=lead_info.get('last_name', ''),
                company_name=lead_info.get('company_name'),
                phone_number=from_number,
                lead_source="whatsapp"
            )
            
            # Store in database
            await LeadService.create_lead(lead_data)
            logger.info(f"Created lead for {from_number}")
            
            # Send welcome message
            response = """Thanks for reaching out to Smartlead CRM! 👋

I'd love to learn more about you. Could you please share:
- Your name
- Company name
- What brings you here today?"""
            
            await self.send_message(from_number, response)
            
            return {"status": "success", "message": "Processed incoming message"}
            
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            raise

    async def get_whatsapp_leads(self) -> Dict:
        """Get all leads that came from WhatsApp"""
        try:
            leads = await LeadService.get_leads_by_source("whatsapp")
            return {
                "status": "success",
                "leads": leads,
                "count": len(leads)
            }
        except Exception as e:
            logger.error(f"Error getting WhatsApp leads: {str(e)}")
            raise

    async def send_message(self, to_number: str, message: str) -> Dict:
        """Send a WhatsApp message"""
        try:
            if not to_number.startswith('whatsapp:'):
                to_number = f'whatsapp:{to_number}'
            
            message = self.client.messages.create(
                from_=f'whatsapp:{self.from_number}',
                body=message,
                to=to_number
            )
            
            logger.info(f"Sent message to {to_number}: {message.sid}")
            return {"status": "success", "message_sid": message.sid}
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise

    async def extract_lead_info(self, message_body: str) -> Dict:
        """Extract lead information using Claude"""
        try:
            prompt = f"""Extract lead information from this message. If any field is missing, use None.
            Required fields: first_name, last_name, company_name
            
            Message: {message_body}
            
            Return only a JSON object with these fields."""

            response = self.claude.beta.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=300,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            lead_info = response.content[0].text
            logger.info(f"Extracted lead info: {lead_info}")
            return lead_info

        except Exception as e:
            logger.error(f"Error extracting lead info: {str(e)}")
            return {} 