"""FRIDAY configuration from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Gemini
    gemini_api_key: str = ""
    google_api_key: str = ""

    # Supabase (optional for now)
    supabase_url: str = ""
    supabase_service_key: str = ""

    # Exa web search
    exa_api_key: str = ""

    # Supermemory
    supermemory_api_key: str = ""

    # OpenRouter
    openrouter_api_key: str = ""

    # Heartbeat
    heartbeat_enabled: bool = True
    heartbeat_interval_seconds: int = 600

    # Logging
    log_level: str = "INFO"

    @property
    def effective_gemini_key(self) -> str:
        return self.gemini_api_key or self.google_api_key


settings = Settings()
