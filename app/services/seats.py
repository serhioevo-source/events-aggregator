import time
import uuid
from dataclasses import dataclass

from app.clients.protocols import EventsProviderProtocol
from app.repositories.protocols import EventRepositoryProtocol


class EventNotFoundError(Exception):
    """Requested event does not exist in the local database."""


class EventNotPublishedError(Exception):
    """Seats are available only for published events."""


@dataclass
class SeatsCacheEntry:
    seats: list[str]
    expires_at: float


class SeatsService:
    def __init__(
        self,
        event_repository: EventRepositoryProtocol,
        provider_client: EventsProviderProtocol,
        cache: dict[uuid.UUID, SeatsCacheEntry],
        cache_ttl_seconds: int,
    ) -> None:
        self.event_repository = event_repository
        self.provider_client = provider_client
        self.cache = cache
        self.cache_ttl_seconds = cache_ttl_seconds

    async def get_available_seats(self, event_id: uuid.UUID) -> list[str]:
        event = await self.event_repository.get_by_id(event_id)

        if event is None:
            raise EventNotFoundError

        if event.status != "published":
            raise EventNotPublishedError

        now = time.monotonic()
        cached = self.cache.get(event_id)

        if cached is not None and cached.expires_at > now:
            return list(cached.seats)

        seats = await self.provider_client.seats(str(event_id))

        self.cache[event_id] = SeatsCacheEntry(
            seats=list(seats),
            expires_at=now + self.cache_ttl_seconds,
        )

        return list(seats)
