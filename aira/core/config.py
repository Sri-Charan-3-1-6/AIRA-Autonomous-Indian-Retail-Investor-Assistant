"""AIRA module: core/config.py"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(..., description="Supabase anonymous key")
    SUPABASE_SERVICE_KEY: str = Field(..., description="Supabase service role key")
    GROQ_API_KEY: str = Field(..., description="Groq API key")
    APP_ENV: str = Field(default="development", description="Application environment")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
