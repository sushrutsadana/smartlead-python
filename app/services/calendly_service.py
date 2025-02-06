import os
import requests
import logging
from typing import Dict, Optional
from ..schemas.lead import LeadStatus, ActivityType

logger = logging.getLogger(__name__)

class CalendlyService:
    def __init__(self, lead_service):
        self.api_token = os.environ.get('CALENDLY_API_TOKEN')
        self.webhook_url = os.environ.get('CALENDLY_WEBHOOK_URL')
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        self.lead_service = lead_service
        self.api_key = os.getenv('CALENDLY_API_KEY')
        self.organization = os.getenv('CALENDLY_ORGANIZATION')
        self.webhook_signing_key = os.getenv('CALENDLY_WEBHOOK_SIGNING_KEY')

    async def setup_webhook(self) -> Dict:
        """
        Sets up or verifies Calendly webhook configuration
        """
        try:
            # Get organization ID first
            org_id = await self.get_organization_id()
            
            # Get existing webhooks
            response = requests.get(
                'https://api.calendly.com/webhook_subscriptions',
                headers=self.headers
            )
            response.raise_for_status()
            
            # Check if our webhook already exists
            webhooks = response.json().get('collection', [])
            webhook_exists = any(w['url'] == self.webhook_url for w in webhooks)
            
            if not webhook_exists:
                # Create webhook subscription
                data = {
                    "url": self.webhook_url,
                    "events": [
                        "invitee.created",
                        "invitee.canceled"
                    ],
                    "organization": f"https://api.calendly.com/organizations/{org_id}",
                    "scope": "organization"
                }
                
                response = requests.post(
                    'https://api.calendly.com/webhook_subscriptions',
                    json=data,
                    headers=self.headers
                )
                response.raise_for_status()
                logger.info("Calendly webhook subscription created")
                
            return {"status": "success", "message": "Webhook setup complete"}
            
        except Exception as e:
            logger.error(f"Error setting up webhook: {str(e)}")
            raise

    async def handle_webhook(self, payload: Dict) -> Dict:
        """Handle Calendly webhook events"""
        try:
            event_type = payload.get('event')
            invitee_email = payload.get('payload', {}).get('email')
            
            if not invitee_email:
                raise ValueError("No email found in webhook payload")
                
            # Find lead by email
            leads = await self.lead_service.get_leads_by_email(invitee_email)
            if not leads:
                logger.warning(f"No lead found for email: {invitee_email}")
                return {"status": "warning", "message": "No lead found"}
                
            lead = leads[0]
            
            if event_type == 'invitee.created':
                # Update lead status to qualified
                await self.lead_service.update_lead_status(
                    lead['id'], 
                    LeadStatus.QUALIFIED
                )
                
                # Log meeting scheduled activity
                meeting_details = payload.get('payload', {})
                activity_data = {
                    "lead_id": lead['id'],
                    "activity_type": ActivityType.MEETING_SCHEDULED,
                    "body": f"""Meeting scheduled:
Start time: {meeting_details.get('start_time')}
End time: {meeting_details.get('end_time')}
Event type: {meeting_details.get('event_type', {}).get('name')}
"""
                }
                await self.lead_service.log_activity(activity_data)
                
            elif event_type == 'invitee.canceled':
                # Log cancellation
                activity_data = {
                    "lead_id": lead['id'],
                    "activity_type": ActivityType.MEETING_CANCELED,
                    "body": f"Meeting canceled: {payload.get('payload', {}).get('cancel_reason', 'No reason provided')}"
                }
                await self.lead_service.log_activity(activity_data)
            
            return {"status": "success", "message": f"Processed {event_type} event"}
            
        except Exception as e:
            logger.error(f"Error handling Calendly webhook: {str(e)}")
            raise

    async def get_organization_id(self) -> str:
        """Get the Calendly organization ID"""
        try:
            response = requests.get(
                'https://api.calendly.com/users/me',
                headers=self.headers
            )
            response.raise_for_status()
            user_data = response.json()
            
            # Get the organization URI from current user
            org_uri = user_data.get('resource', {}).get('current_organization')
            if not org_uri:
                raise ValueError("No organization found for user")
            
            # Extract organization ID from URI
            org_id = org_uri.split('/')[-1]
            return org_id
            
        except Exception as e:
            logger.error(f"Error getting organization ID: {str(e)}")
            raise

def get_calendly_service() -> CalendlyService:
    """
    Factory function to create CalendlyService instance
    """
    return CalendlyService() 