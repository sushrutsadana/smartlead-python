from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import PlainTextResponse
import logging
from typing import Dict
import os
from ..schemas.lead import ActivityType
from ..dependencies import get_lead_service

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meta", tags=["meta"])

# Get environment variables
META_VERIFY_TOKEN = os.environ.get("META_VERIFY_TOKEN", "your_verification_token")
PAGE_ACCESS_TOKEN = os.environ.get("META_PAGE_ACCESS_TOKEN", "")

@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Verify Meta webhook. This endpoint handles the verification challenge 
    from Meta when setting up your webhook.
    """
    try:
        # Get query parameters
        query_params = dict(request.query_params)
        
        mode = query_params.get('hub.mode')
        token = query_params.get('hub.verify_token')
        challenge = query_params.get('hub.challenge')
        
        logger.info(f"Received webhook verification request: mode={mode}, token={token}")
        
        # Verify token
        if mode == 'subscribe' and token == META_VERIFY_TOKEN:
            logger.info("Webhook verification successful")
            # Return the challenge as plain text
            return PlainTextResponse(challenge)
        else:
            logger.warning("Webhook verification failed: invalid token or mode")
            raise HTTPException(status_code=403, detail="Verification failed")
            
    except Exception as e:
        logger.error(f"Error verifying webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def receive_webhook(
    request: Request,
    lead_service = Depends(get_lead_service)
):
    """
    Handle incoming messages from Meta (WhatsApp/Messenger).
    Creates leads and logs activities based on message content.
    """
    try:
        # Parse request body
        body = await request.json()
        logger.info(f"Received Meta webhook: {body}")
        
        # Meta sends a different structure than Twilio
        # Extract entry and messaging data
        entries = body.get('entry', [])
        
        for entry in entries:
            messaging = entry.get('messaging', [])
            for message_event in messaging:
                sender_id = message_event.get('sender', {}).get('id')
                recipient_id = message_event.get('recipient', {}).get('id')
                
                # Get the message content
                message = message_event.get('message', {})
                message_text = message.get('text', '')
                
                logger.info(f"Received message: {message_text} from {sender_id}")
                
                # Check if we have a lead with this ID already
                # You may want to implement a get_lead_by_meta_id function
                existing_leads = await lead_service.get_leads_by_meta_id(sender_id)
                
                if existing_leads:
                    # Log activity for existing lead
                    lead_id = existing_leads[0]['id']
                    activity_data = {
                        "lead_id": lead_id,
                        "activity_type": ActivityType.WHATSAPP_MESSAGE,
                        "body": f"Meta message received: {message_text}"
                    }
                    await lead_service.log_activity(activity_data)
                else:
                    # Create a new lead
                    # Typically you'd want to get more info via the Meta Graph API
                    # But here's a simple implementation
                    lead_data = {
                        "first_name": "Meta",  # Placeholder
                        "last_name": "User",   # Placeholder
                        "meta_id": sender_id,  # Store the Meta ID
                        "lead_source": "meta",
                        "email": f"{sender_id}@placeholder.com"  # Placeholder
                    }
                    
                    # Create the lead
                    new_lead = await lead_service.create_lead(lead_data)
                    
                    # Log activity
                    activity_data = {
                        "lead_id": new_lead['id'],
                        "activity_type": ActivityType.WHATSAPP_MESSAGE,
                        "body": f"First Meta message received: {message_text}"
                    }
                    await lead_service.log_activity(activity_data)
        
        # Meta expects a 200 OK response to acknowledge receipt
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error processing Meta webhook: {str(e)}")
        # Still return 200 to Meta to prevent retries
        return {"status": "error", "message": str(e)} 