from datetime import datetime
from ..schemas.lead import LeadCreate, Activity, ActivityType, LeadStatus
import logging
from fastapi import HTTPException

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
            await self.log_activity(activity_data)
            
            return lead_record
        except Exception as e:
            logger.error(f"Error creating lead: {str(e)}")
            raise

    async def get_leads(self) -> list:
        """Get all leads"""
        try:
            result = self.supabase.table("leads").select("*").execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting leads: {str(e)}")
            raise

    async def get_lead(self, lead_id: str) -> dict:
        """Get a specific lead by ID"""
        try:
            result = self.supabase.table("leads").select("*").eq("id", lead_id).execute()
            if not result.data:
                raise HTTPException(status_code=404, detail=f"Lead with ID {lead_id} not found")
            return result.data[0]
        except Exception as e:
            logger.error(f"Error getting lead: {str(e)}")
            raise

    async def log_activity(self, activity_data: dict) -> dict:
        try:
            result = self.supabase.table("activities").insert(activity_data).execute()
            return result.data[0]
        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")
            raise

    async def update_lead_status(self, lead_id: str, new_status: LeadStatus) -> dict:
        try:
            # Update lead status
            result = self.supabase.table("leads").update({
                "status": new_status
            }).eq("id", lead_id).execute()
            
            if not result.data:
                raise Exception(f"Lead with ID {lead_id} not found")
            
            # Log status change activity
            activity_data = {
                "lead_id": lead_id,
                "activity_type": ActivityType.STATUS_CHANGED,
                "body": f"Lead status changed to {new_status}",
                "activity_datetime": datetime.now().isoformat()
            }
            await self.log_activity(activity_data)
            
            return result.data[0]
        except Exception as e:
            logger.error(f"Error updating lead status: {str(e)}")
            raise

    async def get_leads_by_email(self, email: str) -> list:
        """Get leads by email address"""
        try:
            result = self.supabase.table("leads").select("*").eq("email", email).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting leads by email: {str(e)}")
            raise

    async def mark_as_contacted(self, lead_id: str) -> dict:
        """Mark a lead as contacted if they're in NEW status"""
        try:
            # Get current lead status
            lead = await self.get_lead(lead_id)
            
            # Only update if status is NEW
            if lead.get('status') == LeadStatus.NEW:
                result = await self.update_lead_status(lead_id, LeadStatus.CONTACTED)
                logger.info(f"Updated lead {lead_id} to CONTACTED status")
                return result
            return lead
            
        except Exception as e:
            logger.error(f"Error marking lead as contacted: {str(e)}")
            raise 