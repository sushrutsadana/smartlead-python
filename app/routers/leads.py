from fastapi import APIRouter, HTTPException, Request, Depends, Body, Form
from fastapi.exceptions import RequestValidationError
from ..schemas.lead import LeadCreate, Activity, ActivityType
from datetime import datetime
import logging
from typing import Optional
from pydantic import BaseModel, EmailStr
from ..dependencies import (
    get_lead_service,
    get_whatsapp_sender,
    get_whatsapp_processor
)
from ..services.whatsapp_processor import WhatsAppProcessor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["leads"])

# Add this class for request validation
class EmailRequest(BaseModel):
    subject: str
    body: str
    cc: Optional[str] = None
    bcc: Optional[str] = None

# Option 1: Accept JSON body
class WhatsAppMessage(BaseModel):
    phone_number: str
    message: str

@router.post("/")
async def create_lead(
    lead: LeadCreate,
    lead_service = Depends(get_lead_service)
):
    try:
        lead_record = await lead_service.create_lead(lead)
        return {"status": "success", "data": lead_record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{lead_id}/activities")
async def create_activity(
    lead_id: str, 
    activity: Activity,
    lead_service = Depends(get_lead_service)
):
    try:
        activity_data = activity.dict()
        activity_data["lead_id"] = lead_id
        activity_data["activity_datetime"] = activity_data["activity_datetime"].isoformat()
        
        activity_record = await lead_service.log_activity(activity_data)
        return {"status": "success", "data": activity_record}
    except Exception as e:
        logger.error(f"Error in create_activity: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Comment out or remove these endpoints
# @router.post("/process-emails")
# @router.post("/{lead_id}/call")
# @router.post("/{lead_id}/send-email")

@router.post("/process-whatsapp")
async def process_whatsapp(
    whatsapp_processor: WhatsAppProcessor = Depends(get_whatsapp_processor)
):
    try:
        result = await whatsapp_processor.process_incoming_messages()
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Error processing WhatsApp messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/whatsapp/check-messages")
async def check_whatsapp_messages(
    whatsapp_processor: WhatsAppProcessor = Depends(get_whatsapp_processor)
):
    """Check and process recent WhatsApp messages"""
    try:
        result = await whatsapp_processor.check_messages()
        return result
    except Exception as e:
        logger.error(f"Error checking WhatsApp messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(
    request: Request,
    whatsapp_processor: WhatsAppProcessor = Depends(get_whatsapp_processor)
):
    """Handle incoming WhatsApp messages"""
    try:
        form_data = await request.form()
        return await whatsapp_processor.handle_incoming_webhook(dict(form_data))
    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/whatsapp/leads")
async def get_whatsapp_leads(
    whatsapp_processor: WhatsAppProcessor = Depends(get_whatsapp_processor)
):
    """Get all leads that came from WhatsApp"""
    try:
        return await whatsapp_processor.get_whatsapp_leads()
    except Exception as e:
        logger.error(f"Error getting WhatsApp leads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_leads(
    lead_service = Depends(get_lead_service)
):
    """Get all leads"""
    try:
        leads = await lead_service.get_leads()
        return {"status": "success", "data": leads}
    except Exception as e:
        logger.error(f"Error getting leads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{lead_id}")
async def get_lead(
    lead_id: str,
    lead_service = Depends(get_lead_service)
):
    """Get a specific lead"""
    try:
        lead = await lead_service.get_lead(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")
        return {"status": "success", "data": lead}
    except Exception as e:
        logger.error(f"Error getting lead: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{lead_id}/send-whatsapp")
async def send_whatsapp_to_lead(
    lead_id: str,
    message: str,
    lead_service = Depends(get_lead_service),
    whatsapp_sender = Depends(get_whatsapp_sender)
):
    """Send a WhatsApp message to a lead"""
    try:
        # Get lead details
        lead = await lead_service.get_lead(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        if not lead.get('phone_number'):
            raise HTTPException(status_code=400, detail="Lead has no phone number")
            
        # Format the phone number if needed
        phone_number = lead['phone_number']
        if not phone_number.startswith('whatsapp:'):
            phone_number = f'whatsapp:{phone_number}'
            
        # Send message
        result = await whatsapp_sender.send_message(
            to_number=phone_number,
            message=message
        )
        
        # Log activity
        activity_data = {
            "lead_id": lead_id,
            "activity_type": ActivityType.WHATSAPP_MESSAGE,
            "body": f"WhatsApp message sent: {message}"
        }
        await lead_service.log_activity(activity_data)
        
        return {"status": "success", "data": result}
        
    except Exception as e:
        logger.error(f"Error sending WhatsApp message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Add these test endpoints
@router.post("/test/whatsapp/send")
async def test_whatsapp_send(
    message_data: WhatsAppMessage,
    whatsapp_sender = Depends(get_whatsapp_sender)
):
    try:
        # Add some logging to debug
        logger.info(f"Attempting to send message to {message_data.phone_number}")
        logger.info(f"WhatsApp sender instance: {whatsapp_sender}")
        
        result = await whatsapp_sender.send_message(
            to_number=message_data.phone_number,
            message=message_data.message
        )
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error in test send: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test/whatsapp/webhook")
async def test_whatsapp_webhook(
    from_number: str = Form(alias="from_number"),
    message_body: str = Form(alias="message_body"),
    message_sid: str = Form(default="test_message_id", alias="message_sid"),
    whatsapp_processor = Depends(get_whatsapp_processor)
):
    """Test endpoint to simulate incoming WhatsApp webhook"""
    try:
        webhook_data = {
            "From": from_number,
            "Body": message_body,
            "MessageSid": message_sid
        }
        
        logger.info(f"Processing webhook with data: {webhook_data}")
        
        result = await whatsapp_processor.handle_incoming_webhook(webhook_data)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error in test webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))