from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum

class LeadStatus(str, Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    CUSTOMER = "customer"
    DISQUALIFIED = "disqualified"
    REMARKET = "remarket"

class ActivityType(str, Enum):
    EMAIL_SENT = "email_sent"
    CALL_MADE = "call_made"
    CALL_COMPLETED = "call_completed"
    LEAD_CREATED = "lead_created"
    STATUS_CHANGED = "status_changed"
    WHATSAPP_MESSAGE = "whatsapp_message"
    CALL_ANALYZED = "call_analyzed"

class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    company_name: Optional[str] = None
    title: Optional[str] = None
    lead_source: str = "manual"
    status: LeadStatus = LeadStatus.NEW

class Activity(BaseModel):
    activity_type: ActivityType
    body: str
    activity_datetime: datetime = datetime.now()

class Lead(LeadCreate):
    id: str
    created_at: datetime 