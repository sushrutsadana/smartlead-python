import os
import requests
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class CallService:
    def __init__(self):
        self.api_key = os.environ.get('BLAND_AI_API_KEY')
        if not self.api_key:
            raise ValueError("BLAND_AI_API_KEY environment variable is not set")
            
        self.base_url = 'https://api.bland.ai/v1'
        self.headers = {
            'Authorization': self.api_key
        }

    async def make_call(self, phone_number: str, first_name: str, last_name: str, company_name: Optional[str] = None, title: Optional[str] = None) -> Dict:
        """Make a call using BlandAI"""
        try:
            # Format company and title info if available
            company_info = f" from {company_name}" if company_name else ""
            title_info = f", {title}" if title else ""
            
            data = {
                "phone_number": phone_number,
                "task": f"""Your name is Jeremy. You're part of the sales team at Searchlight LLC, a software company that helps mid-market to large-scale enterprises identify opportunities to boost revenue via more effective pricing. You're calling {first_name} {last_name}{title_info}{company_info}.

                Your job is to qualify the lead. Ask about:
                1. Their current pricing challenges
                2. Timeline for implementation
                3. Try to schedule a demo

                Be professional and empathetic.""",
                "model": "base",
                "language": "en",
                "voice": "nat",
                "max_duration": 12,
            }

            # Log the request data (excluding sensitive info)
            logger.info(f"Making call to {phone_number}")
            
            response = requests.post(
                f'{self.base_url}/calls',
                json=data,
                headers=self.headers
            )
            
            response.raise_for_status()
            logger.info(f"Successfully initiated call to {phone_number}")
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error making call: {str(e)}")
            raise Exception(f"Failed to make call: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error making call: {str(e)}")
            raise