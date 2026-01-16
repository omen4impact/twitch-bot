"""Main entry point - runs Twitch IRC client and FastAPI server concurrently."""

import asyncio
import signal
import sys
from pathlib import Path

import structlog
import uvicorn

# Add parent directory to path for imports when running as module
sys.path.insert(0, str(Path(__file__).parent.parent))

from handler.config import get_settings
from handler.twitch_client import create_bot
from handler.webhook_server import app, set_twitch_bot


def setup_logging() -> None:
    """Configure structured logging."""
    settings = get_settings()
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    import logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level.upper()),
    )


logger = structlog.get_logger()


class Application:
    """Main application orchestrator."""
    
    def __init__(self):
        self.settings = get_settings()
        self.bot = None
        self.server = None
        self._shutdown_event = asyncio.Event()
    
    async def start_bot(self) -> None:
        """Start the Twitch IRC bot."""
        logger.info("starting_twitch_bot")
        self.bot = await create_bot()
        set_twitch_bot(self.bot)
        
        try:
            await self.bot.start()
        except Exception as e:
            logger.error("bot_error", error=str(e))
            raise
    
    async def start_server(self) -> None:
        """Start the FastAPI server."""
        logger.info(
            "starting_webhook_server",
            host=self.settings.handler_host,
            port=self.settings.handler_port,
        )
        
        config = uvicorn.Config(
            app=app,
            host=self.settings.handler_host,
            port=self.settings.handler_port,
            log_level=self.settings.log_level.lower(),
            access_log=True,
        )
        self.server = uvicorn.Server(config)
        
        try:
            await self.server.serve()
        except Exception as e:
            logger.error("server_error", error=str(e))
            raise
    
    async def shutdown(self) -> None:
        """Gracefully shutdown all services."""
        logger.info("initiating_shutdown")
        
        if self.bot:
            await self.bot.close()
            logger.info("bot_closed")
        
        if self.server:
            self.server.should_exit = True
            logger.info("server_stopped")
        
        self._shutdown_event.set()
    
    def handle_signal(self, sig: signal.Signals) -> None:
        """Handle shutdown signals."""
        logger.info("received_signal", signal=sig.name)
        asyncio.create_task(self.shutdown())
    
    async def run(self) -> None:
        """Run the application."""
        # Setup signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: self.handle_signal(s),
            )
        
        logger.info(
            "application_starting",
            channel=self.settings.twitch_channel,
            webhook_port=self.settings.handler_port,
        )
        
        # Run bot and server concurrently
        try:
            await asyncio.gather(
                self.start_bot(),
                self.start_server(),
                return_exceptions=True,
            )
        except Exception as e:
            logger.error("application_error", error=str(e))
        finally:
            await self.shutdown()


def main() -> None:
    """Main entry point."""
    setup_logging()
    
    logger.info("twitch_bot_handler_starting")
    
    app_instance = Application()
    
    try:
        asyncio.run(app_instance.run())
    except KeyboardInterrupt:
        logger.info("interrupted_by_user")
    except Exception as e:
        logger.error("fatal_error", error=str(e))
        sys.exit(1)
    
    logger.info("application_stopped")


if __name__ == "__main__":
    main()
