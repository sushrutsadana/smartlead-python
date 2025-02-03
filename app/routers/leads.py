from fastapi import APIRouter, HTTPException, Request, Depends, Body
from fastapi.exceptions import RequestValidationError
from ..schemas.lead import LeadCreate, Activity
from datetime import datetime
import logging
from typing import Optional
from pydantic import BaseModel, EmailStr
from ..main import (
    lead_service,
    email_service,
    email_processor,
    call_service,
    whatsapp_service
)

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

@router.post("/")
async def create_lead(lead: LeadCreate):
    try:
        lead_record = await lead_service.create_lead(lead)
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
        
        activity_record = await lead_service.log_activity(activity_data)
        return {"status": "success", "data": activity_record}
    except Exception as e:
        logger.error(f"Error in create_activity: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-emails")
async def process_emails():
    try:
        # Use the initialized email_processor from dependencies
        result = await email_processor.process_new_emails()
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Error processing emails: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{lead_id}/call")
async def make_call_to_lead(lead_id: str):
    try:
        # Get lead's phone number from database
        lead = await lead_service.get_lead(lead_id)
        if not lead.get('phone_number'):
            raise HTTPException(status_code=400, detail="Lead has no phone number")

        # Use the initialized call_service
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
        await lead_service.log_activity(activity_data)

        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-whatsapp")
async def process_whatsapp():
    try:
        # Use the initialized whatsapp_service
        result = await whatsapp_service.process_incoming_messages()
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Error processing WhatsApp messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/whatsapp/check-messages")
async def check_whatsapp_messages():
    """Check and process recent WhatsApp messages"""
    try:
        whatsapp = whatsapp_service
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
        whatsapp = whatsapp_service
        return await whatsapp.handle_incoming_webhook(dict(form_data))
    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/whatsapp/leads")
async def get_whatsapp_leads():
    """Get all leads that came from WhatsApp"""
    try:
        whatsapp = whatsapp_service
        return await whatsapp.get_whatsapp_leads()
    except Exception as e:
        logger.error(f"Error getting WhatsApp leads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{lead_id}/send-email")
async def send_email_to_lead(
    lead_id: str,
    email_request: EmailRequest
):
    """Send an email to a lead"""
    try:
        # Get lead's email from database
        lead = await lead_service.get_lead(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")
        
        if not lead.get('email'):
            raise HTTPException(status_code=400, detail="Lead has no email address")

        # Use the initialized email service
        result = await email_service.send_email(
            to_email=lead['email'],
            subject=email_request.subject,
            body=email_request.body,
            cc=email_request.cc,
            bcc=email_request.bcc
        )

        # Log the activity
        activity_data = {
            "lead_id": lead_id,
            "activity_type": "email_sent",
            "body": f"Email sent: {email_request.subject}",
            "activity_datetime": datetime.now().isoformat()
        }
        await lead_service.log_activity(activity_data)

        return {"status": "success", "data": result}
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_leads():
    """Get all leads"""
    try:
        leads = await lead_service.get_leads()  # You'll need to implement this method
        return {"status": "success", "data": leads}
    except Exception as e:
        logger.error(f"Error getting leads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{lead_id}")
async def get_lead(lead_id: str):
    """Get a specific lead"""
    try:
        lead = await lead_service.get_lead(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")
        return {"status": "success", "data": lead}
    except Exception as e:
        logger.error(f"Error getting lead: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))