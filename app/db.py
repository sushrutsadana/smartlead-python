from supabase import create_client
from .config import settings
import logging

logger = logging.getLogger(__name__)

try:
    logger.info(f"Attempting to connect to Supabase at URL: {settings.SUPABASE_URL}")
    supabase = create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_KEY
    )
    logger.info("Successfully connected to Supabase")
except Exception as e:
    logger.error(f"Failed to connect to Supabase: {str(e)}")
    raise 