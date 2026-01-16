"""Configuration module using pydantic-settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Twitch Configuration
    twitch_token: str
    twitch_channel: str
    twitch_bot_nick: str
    
    # n8n Webhook Configuration
    n8n_webhook_url: str = "https://tbot.weeel.de/webhook/twitch/message"
    
    # Handler API Configuration
    handler_api_key: str
    handler_host: str = "0.0.0.0"
    handler_port: int = 8765
    
    # Logging
    log_level: str = "INFO"
    
    # EventSub (optional)
    twitch_eventsub_secret: str = ""
    
    @property
    def twitch_token_clean(self) -> str:
        """Return token without 'oauth:' prefix if present."""
        token = self.twitch_token
        if token.startswith("oauth:"):
            return token[6:]
        return token


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
