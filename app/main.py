from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .routers import leads
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Smartlead CRM")

# Add validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # We'll update this with specific domains once frontend is deployed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leads.router)

BASE_URL = os.getenv('VERCEL_URL', 'http://localhost:8000')

@app.get("/")
async def root():
    return {"message": "Smartlead CRM API is running"}

@app.get("/debug")
async def debug():
    """Endpoint to help debug deployment issues"""
    return {
        "status": "running",
        "base_url": BASE_URL,
        "env_vars_set": {
            "supabase_url": bool(os.getenv("SUPABASE_URL")),
            "supabase_key": bool(os.getenv("SUPABASE_KEY")),
            "bland_ai_key": bool(os.getenv("BLAND_AI_API_KEY")),
            "anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY")),
        }
    } 