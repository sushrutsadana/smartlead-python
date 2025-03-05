from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime
import os
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ..dependencies import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])

class GmailConnectRequest(BaseModel):
    access_token: str
    refresh_token: str
    email: str
    expires_at: datetime

@router.post("/gmail-connect")
async def connect_gmail(request: GmailConnectRequest, supabase = Depends(get_supabase)):
    try:
        # Create credentials object to test the tokens
        credentials = Credentials(
            token=request.access_token,
            refresh_token=request.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.environ.get("GOOGLE_CLIENT_ID"),
            client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
            scopes=['https://www.googleapis.com/auth/gmail.send', 
                   'https://www.googleapis.com/auth/gmail.modify']
        )
        
        # Test the credentials by making a simple API call
        service = build('gmail', 'v1', credentials=credentials)
        profile = service.users().getProfile(userId='me').execute()
        
        logger.info(f"Successfully connected Gmail for {request.email}")
        
        # Store the tokens in Supabase
        # First check if an entry exists for this email
        result = supabase.table("gmail_credentials").select("*").eq("email", request.email).execute()
        
        if result.data:
            # Update existing record
            supabase.table("gmail_credentials").update({
                "access_token": request.access_token,
                "refresh_token": request.refresh_token,
                "expires_at": request.expires_at.isoformat(),
                "updated_at": datetime.now().isoformat()
            }).eq("email", request.email).execute()
        else:
            # Create new record
            supabase.table("gmail_credentials").insert({
                "email": request.email,
                "access_token": request.access_token,
                "refresh_token": request.refresh_token,
                "expires_at": request.expires_at.isoformat(),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }).execute()
        
        return {"success": True, "message": "Gmail connected successfully", "email": profile.get('emailAddress')}
    except HttpError as error:
        logger.error(f"Gmail API Error: {error}")
        raise HTTPException(status_code=400, detail=f"Gmail API Error: {error}")
    except Exception as e:
        logger.error(f"Failed to connect Gmail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to connect Gmail: {str(e)}")

@router.post("/gmail-disconnect")
async def disconnect_gmail(email: str, supabase = Depends(get_supabase)):
    try:
        # Remove tokens from Supabase
        result = supabase.table("gmail_credentials").delete().eq("email", email).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail=f"No Gmail connection found for {email}")
        
        logger.info(f"Successfully disconnected Gmail for {email}")
        return {"success": True, "message": f"Gmail disconnected successfully for {email}"}
    except Exception as e:
        logger.error(f"Failed to disconnect Gmail: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to disconnect Gmail: {str(e)}")

@router.get("/gmail-status")
async def get_gmail_status(email: str = None, supabase = Depends(get_supabase)):
    try:
        query = supabase.table("gmail_credentials").select("email, created_at, updated_at, expires_at")
        
        if email:
            query = query.eq("email", email)
            
        result = query.execute()
        
        if email and not result.data:
            return {"connected": False, "email": email}
            
        return {
            "connected": len(result.data) > 0,
            "connections": result.data
        }
    except Exception as e:
        logger.error(f"Failed to get Gmail status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get Gmail status: {str(e)}")

@router.get("/gmail-accounts")
async def get_gmail_accounts(supabase = Depends(get_supabase)):
    """Get all available Gmail accounts"""
    try:
        result = supabase.table("gmail_credentials").select("email, created_at, updated_at").execute()
        
        # Also include the default email from environment variables
        default_email = os.environ.get("GMAIL_USER")
        
        accounts = result.data
        
        # Add the default account if it's not already in the list
        if default_email and not any(account['email'] == default_email for account in accounts):
            accounts.append({
                "email": default_email,
                "created_at": None,
                "updated_at": None,
                "is_default": True
            })
            
        return {
            "accounts": accounts,
            "default_email": default_email
        }
    except Exception as e:
        logger.error(f"Error getting Gmail accounts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get Gmail accounts: {str(e)}") 