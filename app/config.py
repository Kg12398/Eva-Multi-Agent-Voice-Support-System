"""
Application configuration using Pydantic Settings.
All settings are loaded from environment variables / .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Central configuration for the Voice Agent system."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # --- App ---
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    MAX_TURN_LIMIT: int = 20
    ENDPOINTING_SILENCE_MS: int = 700

    # --- Twilio ---
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_PHONE_NUMBER: str

    # --- LiveKit ---
    LIVEKIT_URL: str
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str

    # --- Deepgram ---
    DEEPGRAM_API_KEY: str

    # --- Google Gemini (fallback) ---
    GEMINI_API_KEY: str

    # --- Groq (primary LLM) ---
    GROQ_API_KEY: str = ""

    # --- ElevenLabs (backup TTS - unused) ---
    ELEVENLABS_API_KEY: str = ""

    # --- Sarvam AI (primary TTS) ---
    SARVAM_API_KEY: str = ""
    SARVAM_TTS_SPEAKER: str = "anushka"
    SARVAM_TTS_MODEL: str = "bulbul:v2"
    SARVAM_TTS_LANGUAGE: str = "en-IN"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- PostgreSQL ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/voice_agent"

    # --- AWS S3 ---
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: str = "kg-electropower-recordings"

    # --- Langfuse ---
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # --- Email ---
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    NOTIFICATION_EMAIL: str = ""

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


# Singleton instance
settings = Settings()
