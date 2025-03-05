from pydantic_settings import BaseSettings
from pydantic import HttpUrl, SecretStr
from pydantic import validator

class Settings(BaseSettings):
    # Supabase settings
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Gmail API settings
    GMAIL_CLIENT_ID: str
    GMAIL_CLIENT_SECRET: str
    GMAIL_REFRESH_TOKEN: str
    GMAIL_USER: str
    
    # Claude/Anthropic settings
    ANTHROPIC_API_KEY: str
    
    # Bland AI settings
    BLAND_AI_API_KEY: str
    BLAND_AI_WEBHOOK_URL: str
    
    # Twilio/WhatsApp settings
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_NUMBER: str
    TWILIO_WEBHOOK_URL: str
    
    # Google OAuth settings
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    
    class Config:
        env_file = ".env"

    @validator('BLAND_AI_WEBHOOK_URL')
    def validate_webhook_url(cls, v):
        if not v.startswith('https://'):
            raise ValueError('Webhook URL must use HTTPS')
        return v

settings = Settings() 