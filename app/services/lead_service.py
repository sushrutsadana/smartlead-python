from datetime import datetime
from ..db import supabase
from ..schemas.lead import LeadCreate, Activity, ActivityType
import logging

logger = logging.getLogger(__name__)

class LeadService:
    @staticmethod
    async def create_lead(lead: LeadCreate) -> dict:
        # Create lead in Supabase
        lead_data = lead.dict()
        lead_data["created_at"] = datetime.now().isoformat()
        
        result = supabase.table("leads").insert(lead_data).execute()
        lead_record = result.data[0]
        
        # Log lead creation activity
        activity_data = {
            "lead_id": lead_record["id"],
            "activity_type": ActivityType.LEAD_CREATED,
            "body": "Lead created in system",
            "activity_datetime": datetime.now().isoformat()
        }
        supabase.table("activities").insert(activity_data).execute()
        
        return lead_record
    
    @staticmethod
    async def log_activity(activity_data: dict) -> dict:
        try:
            result = supabase.table("activities").insert(activity_data).execute()
            return result.data[0]
        except Exception as e:
            logger.error(f"Error in log_activity: {str(e)}")
            raise

    @staticmethod
    async def get_lead(lead_id: str) -> dict:
        try:
            result = supabase.table("leads").select("*").eq("id", lead_id).execute()
            if not result.data:
                raise Exception(f"Lead with ID {lead_id} not found")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error getting lead: {str(e)}")
            raise 