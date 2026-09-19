import asyncio
import logging
from datetime import UTC, datetime

from app.clients.events_provider import EventsProviderClient
from app.core.config import settings
from app.db.session import async_session_factory
from app.repositories.events import EventRepository
from app.repositories.sync_state import SyncStateRepository
from app.services.sync import SyncEventsService

logger = logging.getLogger(__name__)

sync_lock = asyncio.Lock()


async def run_events_sync() -> int:
    async with sync_lock:
        previous_changed_at = None

        try:
            async with async_session_factory() as session:
                state_repository = SyncStateRepository(session)
                state = await state_repository.get()

                if state is not None:
                    previous_changed_at = state.last_changed_at

                service = SyncEventsService(
                    event_repository=EventRepository(session),
                    sync_state_repository=state_repository,
                    provider_client=EventsProviderClient(
                        base_url=settings.events_provider_base_url,
                        api_key=settings.events_provider_api_key,
                    ),
                )

                count = await service.sync()
                await session.commit()

                return count

        except Exception:
            logger.exception("Events synchronization failed")

            async with async_session_factory() as failed_session:
                failed_repository = SyncStateRepository(failed_session)

                await failed_repository.save(
                    last_sync_time=datetime.now(UTC),
                    last_changed_at=previous_changed_at,
                    sync_status="failed",
                )

                await failed_session.commit()

            raise
