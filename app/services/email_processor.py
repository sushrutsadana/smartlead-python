from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from base64 import urlsafe_b64decode
import anthropic
import os
import json
import logging
from typing import Dict
from ..schemas.lead import LeadCreate
from .lead_service import LeadService
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class EmailProcessor:
    def __init__(self, lead_service: LeadService):
        # Gmail setup
        self.gmail_user = os.environ.get('GMAIL_USER')
        self.gmail = build('gmail', 'v1', credentials=Credentials.from_authorized_user_info({
            'client_id': os.environ.get('GMAIL_CLIENT_ID'),
            'client_secret': os.environ.get('GMAIL_CLIENT_SECRET'),
            'refresh_token': os.environ.get('GMAIL_REFRESH_TOKEN')
        }, ['https://www.googleapis.com/auth/gmail.modify']))
        
        # Claude setup
        self.claude = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        
        # Lead service
        self.lead_service = lead_service

    def _extract_email_data(self, message: Dict) -> Dict:
        """Extract relevant data from email message"""
        email_data = {}
        
        headers = message['payload']['headers']
        email_data['subject'] = next(
            (h['value'] for h in headers if h['name'].lower() == 'subject'),
            'No Subject'
        )
        
        from_header = next(
            (h['value'] for h in headers if h['name'].lower() == 'from'),
            ''
        )
        import re
        email_match = re.search(r'<(.+?)>', from_header)
        email_data['from'] = email_match.group(1) if email_match else from_header

        # Get message body
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    email_data['body'] = urlsafe_b64decode(data).decode()
                    break
        else:
            data = message['payload']['body'].get('data', '')
            email_data['body'] = urlsafe_b64decode(data).decode()

        return email_data

    async def _extract_lead_info(self, email_body: str, sender_email: str) -> Dict:
        """Extract lead information from email using Claude"""
        try:
            prompt = f"""
            Extract lead information from this email and return a JSON object. If any field is not found, use reasonable defaults.
            Required fields (must provide defaults if not found):
            - first_name: if not found, use "Unknown"
            - last_name: if not found, use "Unknown"
            
            Optional fields (only include if found in email):
            - phone_number
            - company_name
            - title

            Email content:
            {email_body}

            Return only the JSON object, nothing else. Make sure all required fields have values.
            """

            response = self.claude.beta.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=300,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse Claude's response
            lead_data = json.loads(response.content[0].text)
            
            # Always use the sender_email
            lead_data = {
                "first_name": lead_data.get("first_name", "Unknown"),
                "last_name": lead_data.get("last_name", "Unknown"),
                "email": sender_email,
                "phone_number": lead_data.get("phone_number"),
                "company_name": lead_data.get("company_name"),
                "title": lead_data.get("title"),
                "lead_source": "email"
            }

            logger.info(f"Extracted lead data: {lead_data}")
            return lead_data

        except Exception as e:
            logger.error(f"Error extracting lead info: {str(e)}")
            return {
                "first_name": "Unknown",
                "last_name": "Unknown",
                "email": sender_email,
                "phone_number": None,
                "company_name": None,
                "title": None,
                "lead_source": "email"
            }

    async def process_new_emails(self):
        """Main function to process new emails and create leads"""
        try:
            # Get unread emails
            results = self.gmail.users().messages().list(
                userId=self.gmail_user,
                q='is:unread'
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                return "No new emails to process"

            processed_count = 0
            for message in messages:
                try:
                    # Get full email data
                    email_data = self.gmail.users().messages().get(
                        userId=self.gmail_user,
                        id=message['id']
                    ).execute()

                    # Extract email content
                    decoded_email = self._extract_email_data(email_data)
                    
                    # Extract lead data using Claude
                    lead_data = await self._extract_lead_info(
                        decoded_email['body'], 
                        decoded_email['from']
                    )
                    
                    # Create lead
                    lead = LeadCreate(**lead_data)
                    await self.lead_service.create_lead(lead)
                    
                    # Mark email as read
                    self.gmail.users().messages().modify(
                        userId=self.gmail_user,
                        id=message['id'],
                        body={'removeLabelIds': ['UNREAD']}
                    ).execute()

                    processed_count += 1
                    logger.info(f"Processed email from: {decoded_email['from']}")

                except Exception as e:
                    logger.error(f"Error processing individual email: {str(e)}")
                    continue

            return f"Processed {processed_count} emails"
            
        except Exception as e:
            logger.error(f"Error in process_new_emails: {str(e)}")
            raise

    async def process_email_content(self, email_content: str):
        client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        response = client.beta.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": f"Please analyze this email content: {email_content}"
            }]
        )
        
        return response.content[0].text 