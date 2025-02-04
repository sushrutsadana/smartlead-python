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
            # Define specific questions for better analysis
            data = {
                "goal": "Analyze the sales call to determine lead interest, objections, and next steps",  # Required field
                "questions": [
                    ["Did the lead express interest in scheduling a demo?", "boolean"],
                    ["What were the main objections or concerns?", "string"],
                    ["What is their timeline for implementation?", "string"],
                    ["Overall sentiment of the call", "positive/negative/neutral"],
                    ["Next steps discussed", "string"]
                ]
            }

            response = requests.post(
                f'{self.base_url}/calls/{call_id}/analyze',
                json=data,
                headers=self.headers
            )
            
            response.raise_for_status()
            raw_analysis = response.json()
            
            # Log the raw response for debugging
            logger.info(f"Raw analysis response: {raw_analysis}")

            # Create formatted analysis directly from raw response
            formatted_analysis = {
                "status": raw_analysis.get("status"),
                "message": raw_analysis.get("message"),
                "answers": {
                    "interested_in_demo": raw_analysis.get("answers", [None])[0],
                    "objections": raw_analysis.get("answers", [None, None])[1] or "None mentioned",
                    "timeline": raw_analysis.get("answers", [None, None, None])[2] or "Not discussed",
                    "sentiment": raw_analysis.get("answers", [None, None, None, None])[3] or "neutral",
                    "next_steps": raw_analysis.get("answers", [None, None, None, None, None])[4] or "No specific next steps"
                },
                "call_details": {
                    "call_id": call_id,
                    "analysis_timestamp": datetime.now().isoformat(),
                    "credits_used": raw_analysis.get("credits_used", 0)
                }
            }

            logger.info(f"Formatted analysis: {formatted_analysis}")
            return formatted_analysis

        except Exception as e:
            logger.error(f"Error analyzing call: {str(e)}")
            logger.error(f"Full error details: ", exc_info=True)
            raise