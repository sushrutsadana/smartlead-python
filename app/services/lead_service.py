from datetime import datetime
from ..schemas.lead import LeadCreate, Activity, ActivityType
import logging

logger = logging.getLogger(__name__)

class LeadService:
    def __init__(self, supabase):
        self.supabase = supabase

    async def create_lead(self, lead: LeadCreate) -> dict:
        try:
            # Create lead in Supabase
            lead_data = lead.dict()
            lead_data["created_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("leads").insert(lead_data).execute()
            lead_record = result.data[0]
            
            # Log lead creation activity
            activity_data = {
                "lead_id": lead_record["id"],
                "activity_type": ActivityType.LEAD_CREATED,
                "body": "Lead created in system",
                "activity_datetime": datetime.now().isoformat()
            }
            self.supabase.table("activities").insert(activity_data).execute()
            
            return lead_record
        except Exception as e:
            logger.error(f"Error creating lead: {str(e)}")
            raise

    async def get_lead(self, lead_id: str) -> dict:
        try:
            result = self.supabase.table("leads").select("*").eq("id", lead_id).execute()
            if not result.data:
                raise Exception(f"Lead with ID {lead_id} not found")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error getting lead: {str(e)}")
            raise

    async def log_activity(self, activity_data: dict) -> dict:
        try:
            result = self.supabase.table("activities").insert(activity_data).execute()
            return result.data[0]
        except Exception as e:
            logger.error(f"Error in log_activity: {str(e)}")
            raise 