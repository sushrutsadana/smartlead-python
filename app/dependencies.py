from fastapi import Depends
from supabase import create_client
import os

def get_supabase():
    return create_client(
        supabase_url=os.environ.get("SUPABASE_URL"),
        supabase_key=os.environ.get("SUPABASE_KEY")
    ) 