from pydantic_settings import BaseSettings

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
    BLAND_AI_API_KEY: str  # Remove BLAND_AI_ORG_ID
    
    # Twilio/WhatsApp settings
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_WHATSAPP_NUMBER: str
    TWILIO_WEBHOOK_URL: str
    
    class Config:
        env_file = ".env"

settings = Settings() 