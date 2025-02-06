import os
import requests
import logging
from typing import Dict, Optional
from datetime import datetime
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class CallService:
    def __init__(self):
        self.api_key = os.environ.get('BLAND_AI_API_KEY')
        if not self.api_key:
            raise ValueError("BLAND_AI_API_KEY environment variable is not set")
            
        self.base_url = 'https://api.bland.ai/v1'
        self.webhook_url = os.environ.get('BLAND_AI_WEBHOOK_URL')  # Get from env
        if not self.webhook_url:
            raise ValueError("BLAND_AI_WEBHOOK_URL environment variable is not set")
            
        self.headers = {
            'Authorization': self.api_key
        }

    async def make_call(
        self, 
        phone_number: str, 
        first_name: str, 
        last_name: str, 
        prompt: str, 
        lead_id: str, 
        language: str = "en",
        voice: str = "nat",
        max_duration: int = 12,
        company_name: Optional[str] = None, 
        title: Optional[str] = None
    ) -> Dict:
        """Make a call using BlandAI"""
        try:
            # Format company and title info if available
            company_info = f" from {company_name}" if company_name else ""
            title_info = f", {title}" if title else ""
            
            data = {
                "phone_number": phone_number,
                "task": prompt,
                "model": "base",
                "language": language,
                "voice": voice,
                "max_duration": max_duration,
                "webhook": self.webhook_url,
                "record": True,
                "metadata": {
                    "lead_id": lead_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "company_name": company_name,
                    "title": title
                }
            }

            logger.info(f"Making call to {phone_number} in language: {language}")
            
            response = requests.post(
                f'{self.base_url}/calls',
                json=data,
                headers=self.headers
            )
            
            # Add more detailed error handling
            if response.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            response.raise_for_status()
            response_data = response.json()
            
            call_id = response_data.get('call_id')
            logger.info(f"Successfully initiated call to {phone_number} with call_id: {call_id}")
            
            return {
                "status": "success",
                "call_id": call_id,
                "data": response_data
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error making call: {str(e)}")
            raise Exception(f"Failed to make call: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error making call: {str(e)}")
            raise

    async def analyze_call(self, call_id: str) -> Dict:
        """Analyze a completed call using BlandAI's analysis endpoint"""
        try:
            # First check if call is completed
            call_status = await self.get_call_status(call_id)
            if call_status != "completed":
                raise HTTPException(
                    status_code=400, 
                    detail=f"Call {call_id} is not completed yet. Status: {call_status}"
                )

            url = f'{self.base_url}/calls/{call_id}/analyze'
            logger.info(f"Analyzing call {call_id} at URL: {url}")
            
            # Format questions according to Bland AI docs
            data = {
                "goal": "Analyze the sales call to determine lead interest, objections, and next steps",
                "questions": [
                    ["Did the lead express interest in scheduling a demo?", "boolean"],
                    ["What were the main objections or concerns?", "string"],
                    ["What is their timeline for implementation?", "string"],
                    ["Overall sentiment of the call", "string"],
                    ["Next steps discussed", "string"]
                ]
            }

            response = requests.post(
                url,
                json=data,
                headers=self.headers
            )
            
            logger.info(f"Raw response: {response.text}")
            response.raise_for_status()
            
            raw_analysis = response.json()
            return raw_analysis

        except Exception as e:
            logger.error(f"Error analyzing call: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_call_status(self, call_id: str) -> str:
        """Get the current status of a call"""
        try:
            response = requests.get(
                f'{self.base_url}/calls/{call_id}',
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            return data.get('status', 'unknown')
        except Exception as e:
            logger.error(f"Error getting call status: {str(e)}")
            raise