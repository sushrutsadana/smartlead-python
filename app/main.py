from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase import create_client
from .schemas.lead import LeadCreate, Activity, ActivityType
from .services.lead_service import LeadService
from .services.call_service import CallService
from .services.email_processor import EmailProcessor
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Supabase client
try:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
    supabase = create_client(
        supabase_url=supabase_url,
        supabase_key=supabase_key
    )
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")
    raise

# Initialize services
lead_service = LeadService(supabase)
call_service = CallService()
email_processor = EmailProcessor(lead_service)

app = FastAPI(title="Smartlead CRM")

# Basic CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

@app.get("/")
async def root() -> dict:
    return {"message": "API is running"}

@app.get("/health")
async def health_check() -> dict:
    return {
        "status": "healthy",
        "version": "1.0"
    }

@app.get("/test-db")
async def test_db() -> dict:
    try:
        # Try to fetch one record from leads table
        result = supabase.table("leads").select("*").limit(1).execute()
        return {
            "status": "connected",
            "message": "Successfully connected to database",
            "record_count": len(result.data)
        }
    except Exception as e:
        logger.error(f"Database test failed: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

# Lead endpoints
@app.post("/leads")
async def create_lead(lead: LeadCreate) -> dict:
    try:
        lead_record = await lead_service.create_lead(lead)
        return {"status": "success", "data": lead_record}
    except Exception as e:
        logger.error(f"Error creating lead: {str(e)}")
        raise

@app.post("/leads/{lead_id}/activities")
async def create_activity(lead_id: str, activity: Activity) -> dict:
    try:
        activity_data = activity.dict()
        activity_data["lead_id"] = lead_id
        activity_data["activity_datetime"] = activity_data["activity_datetime"].isoformat()
        
        activity_record = await lead_service.log_activity(activity_data)
        return {"status": "success", "data": activity_record}
    except Exception as e:
        logger.error(f"Error creating activity: {str(e)}")
        raise

@app.get("/leads/{lead_id}")
async def get_lead(lead_id: str) -> dict:
    try:
        lead = await lead_service.get_lead(lead_id)
        return {"status": "success", "data": lead}
    except Exception as e:
        logger.error(f"Error getting lead: {str(e)}")
        raise

@app.post("/leads/{lead_id}/call")
async def make_call_to_lead(lead_id: str) -> dict:
    try:
        # Get lead's information
        lead = await lead_service.get_lead(lead_id)
        if not lead.get('phone_number'):
            raise HTTPException(status_code=400, detail="Lead has no phone number")

        # Make the call
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
            "activity_type": ActivityType.CALL_MADE,
            "body": "Automated call initiated",
            "activity_datetime": datetime.now().isoformat()
        }
        await lead_service.log_activity(activity_data)

        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error initiating call: {str(e)}")
        raise

@app.post("/process-emails")
async def process_emails() -> dict:
    """Process new unread emails and create leads"""
    try:
        result = await email_processor.process_new_emails()
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Error processing emails: {str(e)}")
        raise
