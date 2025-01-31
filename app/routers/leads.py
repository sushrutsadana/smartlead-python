from fastapi import APIRouter, HTTPException, Request, Header
from fastapi.exceptions import RequestValidationError
from ..schemas.lead import LeadCreate, Activity
from ..services.lead_service import LeadService
from ..services.email_processor import EmailProcessor
from ..services.call_service import CallService
from ..services.whatsapp_service import WhatsAppService
from datetime import datetime
import logging
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["leads"])

@router.post("/")
async def create_lead(lead: LeadCreate):
    try:
        lead_record = await LeadService.create_lead(lead)
        return {"status": "success", "data": lead_record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{lead_id}/activities")
async def create_activity(lead_id: str, activity: Activity):
    try:
        # Convert activity to dict using dict() instead of model_dump()
        activity_data = activity.dict()
        activity_data["lead_id"] = lead_id
        # Convert datetime to ISO format string
        activity_data["activity_datetime"] = activity_data["activity_datetime"].isoformat()
        
        activity_record = await LeadService.log_activity(activity_data)
        return {"status": "success", "data": activity_record}
    except Exception as e:
        logger.error(f"Error in create_activity: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-emails")
async def process_emails():
    try:
        processor = EmailProcessor()
        result = await processor.process_new_emails()
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Error processing emails: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 

@router.post("/{lead_id}/call")
async def make_call_to_lead(lead_id: str):
    try:
        # Get lead's phone number from database
        lead = await LeadService.get_lead(lead_id)
        if not lead.get('phone_number'):
            raise HTTPException(status_code=400, detail="Lead has no phone number")

        # Make the call
        call_service = CallService()
        result = await call_service.make_call(
            phone_number=lead['phone_number'],
            first_name=lead['first_name'],
            last_name=lead['last_name'],
            company_name=lead.get('company_name'),
            title=lead.get('title')
        )

        # Log activity
        activity_data = {
            "lead_id": lead_id,
            "activity_type": "call_made",
            "body": "Automated call initiated",
            "activity_datetime": datetime.now().isoformat()
        }
        await LeadService.log_activity(activity_data)

        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-whatsapp")
async def process_whatsapp():
    try:
        whatsapp = WhatsAppService()
        result = await whatsapp.process_incoming_messages()
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Error processing WhatsApp messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/whatsapp/check-messages")
async def check_whatsapp_messages():
    """Check and process recent WhatsApp messages"""
    try:
        whatsapp = WhatsAppService()
        result = await whatsapp.check_messages()
        return result
    except Exception as e:
        logger.error(f"Error checking WhatsApp messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):
    """Handle incoming WhatsApp messages"""
    try:
        form_data = await request.form()
        whatsapp = WhatsAppService()
        return await whatsapp.handle_incoming_webhook(dict(form_data))
    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/whatsapp/leads")
async def get_whatsapp_leads():
    """Get all leads that came from WhatsApp"""
    try:
        whatsapp = WhatsAppService()
        return await whatsapp.get_whatsapp_leads()
    except Exception as e:
        logger.error(f"Error getting WhatsApp leads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))