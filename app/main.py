from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase import create_client
import logging
import os
from dotenv import load_dotenv
from datetime import datetime
from .services.calendly_service import get_calendly_service

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
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
    supabase = create_client(
        supabase_url=supabase_url,
        supabase_key=supabase_key
    )
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")
    raise

app = FastAPI(title="Smartlead CRM")

# Basic CORS middleware - keep it permissive for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers after app initialization
from .routers import leads
app.include_router(leads.router)

# Simple error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

@app.get("/")
async def root():
    return {"message": "API is running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0"
    }

# Required environment variables check
required_env_vars = [
    'SUPABASE_URL',
    'SUPABASE_KEY',
    'GMAIL_CLIENT_ID',
    'GMAIL_CLIENT_SECRET',
    'GMAIL_REFRESH_TOKEN',
    'GMAIL_USER',
    'BLAND_AI_API_KEY',
    'BLAND_AI_WEBHOOK_URL',
    'TWILIO_ACCOUNT_SID',
    'TWILIO_AUTH_TOKEN',
    'TWILIO_WHATSAPP_NUMBER'
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

@app.on_event("startup")
async def startup_event():
    try:
        # Initialize Calendly webhook
        calendly_service = get_calendly_service()
        await calendly_service.setup_webhook()
        logger.info("Calendly webhook setup completed")
    except Exception as e:
        logger.error(f"Error setting up Calendly webhook: {str(e)}")
        # Don't raise - allow app to start even if webhook setup fails
