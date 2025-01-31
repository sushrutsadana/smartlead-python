from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.routers import leads

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Smartlead CRM")

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(leads.router)

@app.get("/")
async def root():
    return {"message": "Smartlead CRM API is running"}

# Export the FastAPI app for Vercel
export_app = app 