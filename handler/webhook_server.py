"""FastAPI Webhook Server for n8n communication."""

from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
import structlog

from .config import get_settings, Settings

logger = structlog.get_logger()

# Global reference to the Twitch bot (set by main.py)
_twitch_bot = None


def set_twitch_bot(bot) -> None:
    """Set the global Twitch bot reference."""
    global _twitch_bot
    _twitch_bot = bot


def get_twitch_bot():
    """Get the global Twitch bot reference."""
    return _twitch_bot


class SendMessageRequest(BaseModel):
    """Request model for sending chat messages."""
    channel: str
    message: str


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    connected: bool
    channel: Optional[str] = None
    bot_name: Optional[str] = None


def verify_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> bool:
    """Verify the API key from request header."""
    if x_api_key != settings.handler_api_key:
        logger.warning("invalid_api_key_attempt")
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("webhook_server_starting")
    yield
    logger.info("webhook_server_stopping")


app = FastAPI(
    title="Twitch Bot Handler API",
    description="Webhook server for n8n integration",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check the health status of the bot and connections."""
    bot = get_twitch_bot()
    
    if bot is None:
        return HealthResponse(
            status="initializing",
            connected=False,
        )
    
    settings = get_settings()
    
    return HealthResponse(
        status="healthy" if bot.is_connected else "disconnected",
        connected=bot.is_connected,
        channel=settings.twitch_channel,
        bot_name=bot.nick if hasattr(bot, "nick") else None,
    )


@app.post("/send")
async def send_message(
    request: SendMessageRequest,
    _: bool = Depends(verify_api_key),
) -> dict:
    """Send a message to the Twitch chat."""
    bot = get_twitch_bot()
    
    if bot is None:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    if not bot.is_connected:
        raise HTTPException(status_code=503, detail="Bot not connected to Twitch")
    
    success = await bot.send_chat_message(request.channel, request.message)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send message")
    
    logger.info(
        "message_sent_via_api",
        channel=request.channel,
        message_length=len(request.message),
    )
    
    return {
        "success": True,
        "channel": request.channel,
        "message": request.message,
    }


@app.get("/")
async def root() -> dict:
    """Root endpoint with basic info."""
    return {
        "name": "Twitch Bot Handler",
        "version": "1.0.0",
        "endpoints": ["/health", "/send"],
    }
