from twilio.request_validator import RequestValidator
import logging
from typing import Dict, Optional
import anthropic
from ..config import settings
from ..schemas.lead import LeadCreate, ActivityType
from .lead_service import LeadService
import json

logger = logging.getLogger(__name__)

class WhatsAppProcessor:
    def __init__(self, lead_service: LeadService):
        try:
            self.validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
            self.lead_service = lead_service
            self.claude = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            logger.info("WhatsAppProcessor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WhatsAppProcessor: {str(e)}")
            raise

    async def handle_incoming_webhook(self, webhook_data: Dict) -> Dict:
        """Process an incoming WhatsApp message from webhook"""
        try:
            # Extract message data
            from_number = webhook_data.get('From', '').replace('whatsapp:', '')
            message_body = webhook_data.get('Body', '')
            message_sid = webhook_data.get('MessageSid', '')
            
            logger.info(f"Processing incoming message: {message_body} from {from_number}")
            
            # Check if lead exists
            existing_lead = await self._find_lead_by_phone(from_number)
            
            if existing_lead:
                await self._log_message_activity(
                    lead_id=existing_lead['id'],
                    message=message_body,
                    message_sid=message_sid
                )
            else:
                logger.info("Creating new lead from WhatsApp message")
                lead_info = await self._extract_lead_info(message_body)
                lead_info['phone_number'] = from_number
                lead_info['lead_source'] = 'whatsapp'
                
                new_lead = LeadCreate(**lead_info)
                created_lead = await self.lead_service.create_lead(new_lead)
                
                await self._log_message_activity(
                    lead_id=created_lead['id'],
                    message=message_body,
                    message_sid=message_sid
                )
            
            return {"status": "success", "message": "Processed incoming message"}
            
        except Exception as e:
            logger.error(f"Error processing incoming message: {str(e)}")
            raise

    async def _find_lead_by_phone(self, phone_number: str) -> Optional[Dict]:
        """Find a lead by phone number"""
        try:
            leads = await self.lead_service.get_leads()
            return next(
                (lead for lead in leads if lead.get('phone_number') == phone_number),
                None
            )
        except Exception as e:
            logger.error(f"Error finding lead by phone: {str(e)}")
            raise

    async def _extract_lead_info(self, message: str) -> Dict:
        """Extract lead information from message using Claude"""
        try:
            prompt = """Extract lead information from this message. If information is not found, use reasonable defaults.
            Required fields:
            - first_name (default: "Unknown")
            - last_name (default: "Unknown")
            
            Optional fields (only include if found):
            - company_name
            - title
            
            Message: {message}
            
            Return only a JSON object with these fields."""

            response = self.claude.beta.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                temperature=0,
                messages=[{"role": "user", "content": prompt.format(message=message)}]
            )
            
            lead_info = json.loads(response.content[0].text)
            logger.info(f"Extracted lead info: {lead_info}")
            return lead_info
            
        except Exception as e:
            logger.error(f"Error extracting lead info: {str(e)}")
            return {
                "first_name": "Unknown",
                "last_name": "Unknown"
            }

    async def _log_message_activity(self, lead_id: str, message: str, message_sid: str):
        """Log a WhatsApp message as a lead activity"""
        try:
            activity_data = {
                "lead_id": lead_id,
                "activity_type": ActivityType.WHATSAPP_MESSAGE,
                "body": f"WhatsApp message received: {message}"
            }
            await self.lead_service.log_activity(activity_data)
        except Exception as e:
            logger.error(f"Error logging message activity: {str(e)}")
            raise 