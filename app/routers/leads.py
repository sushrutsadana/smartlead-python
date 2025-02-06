from fastapi import APIRouter, HTTPException, Request, Depends, Body, Form
from fastapi.exceptions import RequestValidationError
from ..schemas.lead import LeadCreate, Activity, ActivityType
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from ..dependencies import (
    get_lead_service,
    get_whatsapp_sender,
    get_whatsapp_processor,
    get_call_service,
    get_email_processor,
    get_email_service,
    get_calendly_service
)
from ..services.whatsapp_processor import WhatsAppProcessor
from ..services.email_processor import EmailProcessor
from ..services.email_service import EmailService
from enum import Enum
import logging

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

# Add this with other request models at the top
class CallLanguage(str, Enum):
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    HINDI = "hi"
    JAPANESE = "ja"
    KOREAN = "ko"
    CHINESE = "zh"

class CallRequest(BaseModel):
    prompt: str
    language: CallLanguage = CallLanguage.ENGLISH  # Default to English
    voice: Optional[str] = "nat"  # Default voice
    max_duration: Optional[int] = 12  # Default duration in minutes

    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "You are calling to discuss their interest in our software solution. Ask about their current challenges and try to schedule a demo.",
                "language": "en",
                "voice": "nat",
                "max_duration": 12
            }
        }

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

@router.post("/{lead_id}/call", response_model=dict, 
    summary="Make an automated call to a lead",
    description="""
    Make an automated call to a lead with customizable language, voice, and duration.
    
    Available languages:
    - en: English (default)
    - es: Spanish
    - fr: French
    - de: German
    - it: Italian
    - pt: Portuguese
    - hi: Hindi
    - ja: Japanese
    - ko: Korean
    - zh: Chinese
    
    Available voices:
    - nat: Natural voice (default)
    - josh
    - florian
    - june
    - paige
    - kiana
    - allie
    """
)
async def make_call_to_lead(
    lead_id: str,
    call_request: CallRequest = Body(...),
    lead_service = Depends(get_lead_service),
    call_service = Depends(get_call_service)
):
    """
    Make an automated call to a lead with custom language and voice settings.
    
    Parameters:
    - **lead_id**: The ID of the lead to call
    - **prompt**: The script/instructions for the AI to follow during the call
    - **language**: The language to use for the call (default: en)
    - **voice**: The voice to use (default: nat)
    - **max_duration**: Maximum call duration in minutes (default: 12)
    
    Returns:
    - Call details including call_id and status
    """
    try:
        # Get lead's information
        lead = await lead_service.get_lead(lead_id)
        if not lead.get('phone_number'):
            raise HTTPException(status_code=400, detail="Lead has no phone number")

        # Mark as contacted before making the call
        await lead_service.mark_as_contacted(lead_id)

        # Make the call with custom prompt and language
        result = await call_service.make_call(
            phone_number=lead['phone_number'],
            first_name=lead['first_name'],
            last_name=lead['last_name'],
            company_name=lead.get('company_name'),
            title=lead.get('title'),
            prompt=call_request.prompt,
            language=call_request.language,
            voice=call_request.voice,
            max_duration=call_request.max_duration,
            lead_id=lead_id
        )

        # Log activity
        activity_data = {
            "lead_id": lead_id,
            "activity_type": ActivityType.CALL_MADE,
            "body": f"""Automated call initiated:
• Language: {call_request.language}
• Voice: {call_request.voice}
• Duration: {call_request.max_duration} minutes
• Prompt: {call_request.prompt[:100]}..."""
        }
        await lead_service.log_activity(activity_data)

        return {
            "status": "success",
            "data": result,
            "message": f"Call initiated in {call_request.language} with {call_request.voice} voice"
        }
    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-emails")
async def process_emails(
    email_processor: EmailProcessor = Depends(get_email_processor)
):
    """Process new unread emails and create leads"""
    try:
        result = await email_processor.process_new_emails()
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Error processing emails: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{lead_id}/send-email")
async def send_email_to_lead(
    lead_id: str,
    email_request: EmailRequest,
    lead_service = Depends(get_lead_service),
    email_service: EmailService = Depends(get_email_service)
):
    """Send an email to a lead"""
    try:
        # Get lead details
        lead = await lead_service.get_lead(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        if not lead.get('email'):
            raise HTTPException(status_code=400, detail="Lead has no email address")
            
        # Mark as contacted before sending email
        await lead_service.mark_as_contacted(lead_id)
            
        # Send email
        result = await email_service.send_email(
            to_email=lead['email'],
            subject=email_request.subject,
            body=email_request.body,
            cc=email_request.cc,
            bcc=email_request.bcc
        )
        
        # Log activity
        activity_data = {
            "lead_id": lead_id,
            "activity_type": ActivityType.EMAIL_SENT,
            "body": f"Email sent: {email_request.subject}"
        }
        await lead_service.log_activity(activity_data)
        
        return {"status": "success", "data": result}
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
            
        # Mark as contacted before sending WhatsApp
        await lead_service.mark_as_contacted(lead_id)
            
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

@router.post("/call/webhook")
async def call_webhook(
    request: Request,
    lead_service = Depends(get_lead_service),
    call_service = Depends(get_call_service)
):
    """Handle BlandAI call webhook"""
    try:
        data = await request.json()
        logger.info(f"Received call webhook data: {data}")
        
        # Extract relevant info from webhook
        call_id = data.get('call_id')
        status = data.get('status')
        duration = data.get('corrected_duration')
        transcript = data.get('concatenated_transcript')
        recording_url = data.get('recording_url')
        disposition = data.get('disposition_tag')
        call_ended_by = data.get('call_ended_by')
        
        # Get metadata
        metadata = data.get('metadata', {})
        lead_id = metadata.get('lead_id')
        first_name = metadata.get('first_name')
        company_name = metadata.get('company_name')
        
        if not lead_id:
            logger.error("No lead_id found in call metadata")
            raise HTTPException(status_code=400, detail="No lead_id in call metadata")

        # Log call completion with more details
        activity_data = {
            "lead_id": lead_id,
            "activity_type": ActivityType.CALL_COMPLETED,
            "body": f"""Call completed:
Status: {status}
Duration: {duration} seconds
Disposition: {disposition or 'Unknown'}
Call Ended By: {call_ended_by or 'Unknown'}
To: {data.get('to')}
From: {data.get('from')}
Started At: {data.get('started_at')}
Ended At: {data.get('end_at')}
Transcript: {transcript[:500] if transcript else 'No transcript available'}...
Recording: {recording_url}"""
        }
        await lead_service.log_activity(activity_data)

        # Only analyze if call is completed and has enough content
        if status == "completed" and transcript:
            try:
                # Analyze the call
                analysis = await call_service.analyze_call(call_id)
                
                if analysis and analysis.get('answers'):
                    # Log analysis as activity with more context
                    analysis_activity = {
                        "lead_id": lead_id,
                        "activity_type": ActivityType.CALL_ANALYZED,
                        "body": f"""Call Analysis Summary for {first_name} at {company_name}:
• Interest in Demo: {analysis['answers'][0] if analysis['answers'][0] is not None else 'Unknown'}
• Objections: {analysis['answers'][1] if analysis['answers'][1] is not None else 'None mentioned'}
• Timeline: {analysis['answers'][2] if analysis['answers'][2] is not None else 'Not discussed'}
• Sentiment: {analysis['answers'][3] if analysis['answers'][3] is not None else 'neutral'}
• Next Steps: {analysis['answers'][4] if analysis['answers'][4] is not None else 'No specific next steps'}
• Disposition Tag: {disposition or 'Unknown'}
• Call Duration: {duration} seconds
• Credits Used: {analysis.get('credits_used', 0)}"""
                    }
                    await lead_service.log_activity(analysis_activity)
                    logger.info(f"Successfully analyzed call {call_id} for lead {lead_id}")
                else:
                    logger.warning(f"Analysis returned no answers for call {call_id}")
                
            except Exception as e:
                logger.error(f"Error analyzing call: {str(e)}")
                # Don't raise exception here - we still want to acknowledge the webhook
                
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error processing call webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{lead_id}/call/{call_id}/analyze")
async def analyze_call_for_lead(
    lead_id: str,
    call_id: str,
    call_service = Depends(get_call_service),
    lead_service = Depends(get_lead_service)
):
    """
    Analyze a completed call using BlandAI's analysis endpoint
    
    - **lead_id**: The ID of the lead
    - **call_id**: The ID of the call to analyze
    """
    try:
        # Analyze the call
        analysis = await call_service.analyze_call(call_id)
        
        # Log the analysis as an activity
        activity_data = {
            "lead_id": lead_id,
            "activity_type": ActivityType.CALL_COMPLETED,
            "body": f"""Call Analysis Summary:
• Interest in Demo: {analysis['answers']['interested_in_demo']}
• Objections: {analysis['answers']['objections']}
• Timeline: {analysis['answers']['timeline']}
• Sentiment: {analysis['answers']['sentiment']}
• Next Steps: {analysis['answers']['next_steps']}"""
        }
        await lead_service.log_activity(activity_data)
        
        return {"status": "success", "data": analysis}
        
    except Exception as e:
        logger.error(f"Error analyzing call: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calendly/webhook")
async def calendly_webhook(
    request: Request,
    calendly_service = Depends(get_calendly_service)
):
    """Handle Calendly webhook events"""
    try:
        payload = await request.json()
        logger.info(f"Received Calendly webhook: {payload}")
        return await calendly_service.handle_webhook(payload)
    except Exception as e:
        logger.error(f"Error in Calendly webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))