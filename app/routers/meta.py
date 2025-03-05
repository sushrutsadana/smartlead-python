from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import PlainTextResponse
import logging
from typing import Dict
import os
import requests
from ..schemas.lead import ActivityType, LeadCreate
from ..dependencies import get_lead_service

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meta", tags=["meta"])

# Get environment variables
META_VERIFY_TOKEN = os.environ.get("META_VERIFY_TOKEN", "your_verification_token")
PAGE_ACCESS_TOKEN = os.environ.get("META_PAGE_ACCESS_TOKEN", "")
IG_TOKEN = os.environ.get("META_IG_TOKEN", "")

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
    Handle incoming messages from Meta platforms (Facebook Messenger, Instagram, WhatsApp).
    Creates leads and logs activities based on message content.
    """
    try:
        # Parse request body
        body = await request.json()
        logger.info(f"Received Meta webhook: {body}")
        
        # Determine which platform the message is from
        object_type = body.get('object', '')
        
        # Extract entry data
        entries = body.get('entry', [])
        
        for entry in entries:
            # First check the object type to distinguish between platforms
            if object_type == 'instagram':
                # This is an Instagram message - might have messaging or changes format
                if 'messaging' in entry:
                    await handle_instagram_message_with_messaging(entry, lead_service)
                elif 'changes' in entry:
                    await handle_changes_message(entry, object_type, lead_service)
                else:
                    logger.warning(f"Unknown Instagram entry format: {entry}")
            elif 'messaging' in entry:
                # This is Facebook Messenger
                await handle_messenger_message(entry, lead_service)
            elif 'changes' in entry:
                # This is likely WhatsApp
                await handle_changes_message(entry, object_type, lead_service)
            else:
                logger.warning(f"Unknown entry format: {entry}")
        
        # Meta expects a 200 OK response to acknowledge receipt
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error processing Meta webhook: {str(e)}")
        # Still return 200 to Meta to prevent retries
        return {"status": "error", "message": str(e)}

async def handle_messenger_message(entry, lead_service):
    """Handle Facebook Messenger messages"""
    try:
        messaging = entry.get('messaging', [])
        for message_event in messaging:
            sender_id = message_event.get('sender', {}).get('id')
            recipient_id = message_event.get('recipient', {}).get('id')
            
            # Get the message content
            message = message_event.get('message', {})
            message_text = message.get('text', '')
            
            logger.info(f"Received Facebook Messenger message: {message_text} from {sender_id}")
            
            # Process the message
            await process_message(
                sender_id=sender_id,
                message_text=message_text,
                platform_name="Facebook Messenger",
                activity_type=ActivityType.MESSENGER_MESSAGE,
                lead_service=lead_service
            )
    except Exception as e:
        logger.error(f"Error handling Messenger message: {str(e)}")
        raise

async def handle_changes_message(entry, object_type, lead_service):
    """Handle messages from the 'changes' array (Instagram or WhatsApp)"""
    try:
        changes = entry.get('changes', [])
        for change in changes:
            field = change.get('field', '')
            value = change.get('value', {})
            
            # Determine if it's Instagram
            is_instagram = (object_type == 'instagram' or 
                           field == 'instagram_messages' or 
                           'instagram' in field)
            
            if is_instagram:
                # Handle Instagram message
                await handle_instagram_message(value, lead_service)
            else:
                # Handle WhatsApp or other changes
                logger.info(f"Received change event for field {field}: {value}")
    except Exception as e:
        logger.error(f"Error handling changes message: {str(e)}")
        raise

async def handle_instagram_message(value, lead_service):
    """Handle Instagram direct messages"""
    try:
        # Instagram messages are usually in value.messages array
        messages = value.get('messages', [])
        
        for msg in messages:
            # Get sender info - structure might vary
            sender_id = msg.get('from', {}).get('id')
            if not sender_id:
                # Try alternate path used by some IG webhooks
                sender_id = msg.get('sender', {}).get('id')
                
            # Get message text
            message_text = msg.get('text', '')
            
            logger.info(f"Received Instagram message: {message_text} from {sender_id}")
            
            # Process the message
            await process_message(
                sender_id=sender_id,
                message_text=message_text,
                platform_name="Instagram",
                activity_type=ActivityType.MESSENGER_MESSAGE,  # Reuse messenger type or create a new one
                lead_service=lead_service
            )
    except Exception as e:
        logger.error(f"Error handling Instagram message: {str(e)}")
        raise

async def handle_instagram_message_with_messaging(entry, lead_service):
    """Handle Instagram messages that use the messaging array format"""
    try:
        messaging = entry.get('messaging', [])
        for message_event in messaging:
            sender_id = message_event.get('sender', {}).get('id')
            recipient_id = message_event.get('recipient', {}).get('id')
            
            # Get the message content
            message = message_event.get('message', {})
            message_text = message.get('text', '')
            
            logger.info(f"Received Instagram message (messaging format): {message_text} from {sender_id}")
            
            # Process the message with Instagram platform name
            await process_message(
                sender_id=sender_id,
                message_text=message_text,
                platform_name="Instagram",
                activity_type=ActivityType.MESSENGER_MESSAGE,  # We could create a new INSTAGRAM_MESSAGE type
                lead_service=lead_service
            )
    except Exception as e:
        logger.error(f"Error handling Instagram messaging: {str(e)}")
        raise

async def process_message(sender_id, message_text, platform_name, activity_type, lead_service):
    """Process a message regardless of platform source"""
    try:
        if not sender_id:
            logger.warning(f"No sender ID found in {platform_name} message")
            return
            
        # Check if we have a lead with this ID already
        existing_leads = await lead_service.get_leads_by_meta_id(sender_id)
        
        if existing_leads:
            # Log activity for existing lead
            lead_id = existing_leads[0]['id']
            activity_data = {
                "lead_id": lead_id,
                "activity_type": activity_type,
                "body": f"{platform_name} message received: {message_text}"
            }
            await lead_service.log_activity(activity_data)
            
            # We don't automatically mark as contacted for inbound messages anymore
        else:
            # Try to get user info from Meta
            user_info = await get_user_info(sender_id, platform_name)
            
            # Create a LeadCreate model instance
            lead_data = LeadCreate(
                first_name=user_info.get('first_name', platform_name),
                last_name=user_info.get('last_name', 'User'),
                email=f"{sender_id}@placeholder.com",  # Placeholder email
                meta_id=sender_id,
                lead_source=platform_name.lower()  # Use platform as source
            )
            
            # Create the lead
            new_lead = await lead_service.create_lead(lead_data)
            
            # Log activity
            activity_data = {
                "lead_id": new_lead['id'],
                "activity_type": activity_type,
                "body": f"First {platform_name} message received: {message_text}"
            }
            await lead_service.log_activity(activity_data)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        raise

async def get_user_info(user_id: str, platform: str = "Facebook") -> Dict:
    """Get user information from Meta Graph API"""
    try:
        # Default info to return if we can't get real data
        default_info = {"first_name": platform, "last_name": "User"}
        
        # Use different tokens based on platform
        token = IG_TOKEN if platform.lower() == "instagram" else PAGE_ACCESS_TOKEN
        
        if not token:
            logger.warning(f"No token available for {platform}, using placeholder user info")
            return default_info
        
        # For Instagram, we need a different approach to get user info
        if platform.lower() == "instagram":
            # Try to get Instagram username at minimum
            url = f"https://graph.facebook.com/v18.0/{user_id}?fields=username&access_token={token}"
            try:
                response = requests.get(url)
                if response.status_code == 200 and "username" in response.json():
                    username = response.json().get("username", "")
                    if username:
                        return {"first_name": username, "last_name": "Instagram"}
            except Exception as ig_err:
                logger.warning(f"Error getting Instagram user info: {str(ig_err)}")
                
            # If we get here, we couldn't get username - use default
            return default_info
            
        # For Facebook, use standard approach  
        url = f"https://graph.facebook.com/{user_id}?fields=first_name,last_name,profile_pic&access_token={token}"
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to get user info from {platform}: {response.text}")
            return default_info
            
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        return default_info 