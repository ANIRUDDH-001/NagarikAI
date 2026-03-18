from supabase import create_client, Client
from app.core.config import settings

def get_supabase_client() -> Client:
    """
    Initialize and return the Python Supabase client.
    Uses credentials automatically validated by Pydantic.
    """
    supabase: Client = create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY
    )
    return supabase

# Expose a singleton-like client instance
db_client = get_supabase_client()
