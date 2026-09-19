import asyncio
import logging

from app.core.config import settings
from app.services.sync_runner import run_events_sync

logger = logging.getLogger(__name__)


async def run_events_sync_worker() -> None:
    while True:
        await asyncio.sleep(settings.sync_interval_seconds)

        try:
            await run_events_sync()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Background events synchronization failed")
