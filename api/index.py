from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import traceback
from app.routers import leads

# Enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log startup information
logger.info("Starting application...")
logger.info(f"Python version: {sys.version}")
logger.info(f"Python path: {sys.path}")

try:
    app = FastAPI(title="Smartlead CRM")
    
    # Log middleware setup
    logger.info("Setting up CORS middleware...")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Log router inclusion
    logger.info("Including routers...")
    app.include_router(leads.router)

    @app.get("/")
    async def root():
        return {"message": "Smartlead CRM API is running"}

    @app.get("/debug")
    async def debug():
        return {
            "python_version": sys.version,
            "python_path": sys.path,
            "loaded_modules": list(sys.modules.keys())
        }

except Exception as e:
    logger.error(f"Startup error: {str(e)}")
    logger.error(traceback.format_exc())
    raise

# Export the FastAPI app for Vercel
export_app = app 