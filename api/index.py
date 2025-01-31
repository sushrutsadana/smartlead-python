import sys
import os
from pathlib import Path
import logging
import traceback

# Add the parent directory to Python path for app imports
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

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
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Directory contents: {os.listdir(parent_dir)}")

try:
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from app.routers import leads
    
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

    # Global error handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        error_msg = f"Global error handler caught: {str(exc)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "traceback": traceback.format_exc(),
                "path": request.url.path
            }
        )

    # Log router inclusion
    logger.info("Including routers...")
    app.include_router(leads.router)

    @app.get("/")
    async def root():
        return {
            "message": "Smartlead CRM API is running",
            "status": "healthy"
        }

    @app.get("/debug")
    async def debug():
        """Endpoint to help debug deployment issues"""
        try:
            from app.db import supabase
            supabase_test = supabase.table("leads").select("*").limit(1).execute()
            db_status = "connected" if supabase_test else "error"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        return {
            "status": "running",
            "python_version": sys.version,
            "python_path": sys.path,
            "cwd": os.getcwd(),
            "dir_contents": os.listdir(parent_dir),
            "env_vars_set": {
                "supabase_url": bool(os.getenv("SUPABASE_URL")),
                "supabase_key": bool(os.getenv("SUPABASE_KEY")),
                "bland_ai_key": bool(os.getenv("BLAND_AI_API_KEY")),
                "anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY")),
            },
            "database_status": db_status
        }

except Exception as e:
    logger.error(f"Startup error: {str(e)}")
    logger.error(traceback.format_exc())
    raise

# Export the FastAPI app for Vercel
app = app 