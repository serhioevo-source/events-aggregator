import logging
from datetime import UTC, datetime

from app.clients.events_provider import EventsPaginator
from app.clients.protocols import EventsProviderProtocol
from app.repositories.protocols import (
    EventRepositoryProtocol,
    SyncStateRepositoryProtocol,
)

logger = logging.getLogger(__name__)

INITIAL_CHANGED_AT = "2000-01-01"


class SyncEventsService:
    def __init__(
        self,
        event_repository: EventRepositoryProtocol,
        sync_state_repository: SyncStateRepositoryProtocol,
        provider_client: EventsProviderProtocol,
    ) -> None:
        self.event_repository = event_repository
        self.sync_state_repository = sync_state_repository
        self.provider_client = provider_client

    async def sync(self) -> int:
        state = await self.sync_state_repository.get()

        if state is not None and state.last_changed_at is not None:
            changed_at = state.last_changed_at.date().isoformat()
            max_changed_at = state.last_changed_at
        else:
            changed_at = INITIAL_CHANGED_AT
            max_changed_at = None

        synced_count = 0

        paginator = EventsPaginator(
            client=self.provider_client,
            changed_at=changed_at,
        )

        async for event_data in paginator:
            await self.event_repository.upsert(event_data)
            synced_count += 1

            event_changed_at = datetime.fromisoformat(event_data["changed_at"])

            if max_changed_at is None or event_changed_at > max_changed_at:
                max_changed_at = event_changed_at

        await self.sync_state_repository.save(
            last_sync_time=datetime.now(UTC),
            last_changed_at=max_changed_at,
            sync_status="success",
        )

        logger.info(
            "Events synchronization completed: %s events",
            synced_count,
        )

        return synced_count
