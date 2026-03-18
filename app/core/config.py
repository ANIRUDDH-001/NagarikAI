import json
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AnyHttpUrl
from typing import List

# Compute paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MASTER_CONFIG_PATH = BASE_DIR / "master_config.json"

class Settings(BaseSettings):
    """
    Application Settings loaded from environment variables.
    Pydantic validating these constraints automatically.
    Raises errors during initialization if required fields are missing.
    """
    
    # 1. FastAPI Settings
    PORT: int = Field(default=8000, description="Port for the FastAPI server")
    DEBUG: bool = Field(default=False, description="Enable debug mode and verbose logging")
    # Using AnyHttpUrl for stricter validation
    CORS_ORIGINS: List[AnyHttpUrl] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins"
    )
    
    # 2. Supabase Integration
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(..., description="Supabase public anon key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., description="Supabase admin service role key")
    
    # 3. AI Services
    GROQ_API_KEY: str = Field(..., description="Groq API key for LLM and STT")
    SARVAM_API_KEY: str = Field(..., description="Sarvam API key for Indic translation/TTS")
    
    # 4. Pipeline Settings
    BATCH_SIZE: int = Field(default=100, description="Default ingestion batch size")
    LOG_LEVEL: str = Field(default="INFO", description="Terminal logging level")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Validates keys and initializes config on startup
settings = Settings()

def load_master_config() -> dict:
    """
    Loads pipeline, scraper, and schema configuration dynamically.
    Instead of hardcoding in Python we keep config parameters here.
    """
    if not MASTER_CONFIG_PATH.exists():
        raise FileNotFoundError(f"Master config not found at: {MASTER_CONFIG_PATH}")
        
    with open(MASTER_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# The master configuration dictionary
master_config = load_master_config()
