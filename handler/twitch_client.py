"""Twitch IRC Client using TwitchIO with auto-reconnect and rate limiting."""

import asyncio
from datetime import datetime
from typing import Optional, Callable, Awaitable

import httpx
import structlog
from twitchio.ext import commands

from .config import get_settings

logger = structlog.get_logger()


class TwitchBot(commands.Bot):
    """Twitch IRC Bot with message forwarding to n8n."""
    
    def __init__(
        self,
        on_message_callback: Optional[Callable[..., Awaitable[None]]] = None,
    ):
        settings = get_settings()
        
        # TwitchIO expects token WITHOUT oauth: prefix
        token = settings.twitch_token
        if token.startswith("oauth:"):
            token = token[6:]  # Remove oauth: prefix
        
        logger.info(
            "initializing_twitch_bot",
            channel=settings.twitch_channel,
            bot_nick=settings.twitch_bot_nick,
            token_length=len(token),
        )
        
        super().__init__(
            token=token,
            prefix="!",
            initial_channels=[settings.twitch_channel],
        )
        
        self.settings = settings
        self._http_client: Optional[httpx.AsyncClient] = None
        self._on_message_callback = on_message_callback
        self._connected = False
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._base_reconnect_delay = 1.0
        
    @property
    def http_client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    @property
    def is_connected(self) -> bool:
        """Check if bot is connected to Twitch."""
        return self._connected
    
    async def event_ready(self) -> None:
        """Called when the bot is ready and connected."""
        self._connected = True
        self._reconnect_attempts = 0
        logger.info(
            "twitch_connected",
            bot_name=self.nick,
            channel=self.settings.twitch_channel,
        )
    
    async def event_error(self, error: Exception, data: str = None) -> None:
        """Called when an error occurs."""
        logger.error(
            "twitch_error",
            error=str(error),
            error_type=type(error).__name__,
            data=data,
        )
    
    async def event_reconnect(self) -> None:
        """Called when reconnecting to Twitch."""
        logger.info("twitch_reconnecting")
        self._connected = False
    
    async def event_channel_joined(self, channel) -> None:
        """Called when the bot joins a channel."""
        logger.info("channel_joined", channel=channel.name)
    
    async def event_message(self, message) -> None:
        """Handle incoming chat messages."""
        # Ignore messages from the bot itself
        if message.echo:
            return
        
        # Extract message data
        msg_data = {
            "channel": message.channel.name if message.channel else "",
            "username": message.author.name if message.author else "",
            "display_name": message.author.display_name if message.author else "",
            "message": message.content,
            "timestamp": datetime.utcnow().isoformat(),
            "badges": self._extract_badges(message),
            "is_mod": message.author.is_mod if message.author else False,
            "is_subscriber": message.author.is_subscriber if message.author else False,
            "is_broadcaster": self._is_broadcaster(message),
        }
        
        logger.debug(
            "message_received",
            username=msg_data["username"],
            message=msg_data["message"][:50],
        )
        
        # Forward to n8n webhook
        await self._forward_to_n8n(msg_data)
        
        # Call custom callback if set
        if self._on_message_callback:
            await self._on_message_callback(msg_data)
        
        # Handle commands (optional, for local commands)
        await self.handle_commands(message)
    
    def _extract_badges(self, message) -> dict:
        """Extract badge information from message."""
        badges = {}
        if message.author and hasattr(message.author, "badges"):
            raw_badges = message.author.badges or {}
            for badge, version in raw_badges.items():
                badges[badge] = version
        return badges
    
    def _is_broadcaster(self, message) -> bool:
        """Check if message author is the broadcaster."""
        if not message.author:
            return False
        badges = self._extract_badges(message)
        return "broadcaster" in badges
    
    async def _forward_to_n8n(self, msg_data: dict) -> None:
        """Forward message data to n8n webhook."""
        try:
            response = await self.http_client.post(
                self.settings.n8n_webhook_url,
                json=msg_data,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self.settings.handler_api_key,
                },
            )
            
            if response.status_code != 200:
                logger.warning(
                    "n8n_webhook_error",
                    status_code=response.status_code,
                    response=response.text[:200],
                )
        except httpx.RequestError as e:
            logger.error("n8n_webhook_failed", error=str(e))
    
    async def send_chat_message(self, channel: str, message: str) -> bool:
        """Send a message to the specified channel."""
        try:
            chan = self.get_channel(channel)
            if chan:
                await chan.send(message)
                logger.info(
                    "message_sent",
                    channel=channel,
                    message=message[:50],
                )
                return True
            else:
                logger.warning("channel_not_found", channel=channel)
                return False
        except Exception as e:
            logger.error("send_message_failed", error=str(e))
            return False
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
        await super().close()


async def create_bot(
    on_message_callback: Optional[Callable[..., Awaitable[None]]] = None,
) -> TwitchBot:
    """Create and return a configured TwitchBot instance."""
    return TwitchBot(on_message_callback=on_message_callback)
