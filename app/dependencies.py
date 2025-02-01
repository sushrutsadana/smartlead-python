from fastapi import Depends
from .services.lead_service import LeadService
from .services.email_processor import EmailProcessor
from .services.call_service import CallService
from supabase import create_client
import os

def get_supabase():
    return create_client(
        supabase_url=os.environ.get("SUPABASE_URL"),
        supabase_key=os.environ.get("SUPABASE_KEY")
    )

def get_lead_service(supabase=Depends(get_supabase)):
    return LeadService(supabase)

def get_email_processor(lead_service=Depends(get_lead_service)):
    return EmailProcessor(lead_service)

def get_call_service():
    return CallService() 