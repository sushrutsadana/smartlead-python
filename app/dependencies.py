from fastapi import Depends, HTTPException
from supabase import create_client
import os
import logging
from .services.lead_service import LeadService
from .services.whatsapp_sender import WhatsAppSender
from .services.whatsapp_processor import WhatsAppProcessor
from .services.email_service import EmailService
from .services.call_service import CallService
from .services.email_processor import EmailProcessor

logger = logging.getLogger(__name__)

def get_supabase():
    try:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("Missing Supabase credentials")
            
        return create_client(
            supabase_url=supabase_url,
            supabase_key=supabase_key
        )
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Database connection failed"
        )

def get_lead_service(supabase = Depends(get_supabase)):
    return LeadService(supabase)

def get_whatsapp_sender():
    try:
        return WhatsAppSender()
    except Exception as e:
        logger.error(f"Failed to initialize WhatsAppSender: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="WhatsApp sender initialization failed"
        )

def get_whatsapp_processor(lead_service = Depends(get_lead_service)):
    try:
        return WhatsAppProcessor(lead_service)
    except Exception as e:
        logger.error(f"Failed to initialize WhatsAppProcessor: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="WhatsApp processor initialization failed"
        )

def get_email_service():
    try:
        return EmailService()
    except Exception as e:
        logger.error(f"Failed to initialize EmailService: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Email service initialization failed"
        )

def get_call_service():
    try:
        return CallService()
    except Exception as e:
        logger.error(f"Failed to initialize CallService: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Call service initialization failed"
        )

def get_email_processor(lead_service = Depends(get_lead_service)):
    try:
        return EmailProcessor(lead_service)
    except Exception as e:
        logger.error(f"Failed to initialize EmailProcessor: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Email processor initialization failed"
        )