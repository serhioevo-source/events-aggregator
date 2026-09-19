import uuid
from datetime import datetime
from typing import Protocol

from app.models.event import Event
from app.models.sync_state import SyncState
from app.models.ticket import Ticket


class EventRepositoryProtocol(Protocol):
    async def upsert(self, event_data: dict) -> None: ...

    async def list_events(
        self,
        date_from: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Event], int]: ...

    async def get_by_id(self, event_id: uuid.UUID) -> Event | None: ...


class SyncStateRepositoryProtocol(Protocol):
    async def get(self) -> SyncState | None: ...

    async def save(
        self,
        *,
        last_sync_time: datetime,
        last_changed_at: datetime | None,
        sync_status: str,
    ) -> None: ...


class TicketRepositoryProtocol(Protocol):
    async def create(
        self,
        *,
        ticket_id: uuid.UUID,
        event_id: uuid.UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> Ticket: ...

    async def get_by_id(
        self,
        ticket_id: uuid.UUID,
    ) -> Ticket | None: ...

    async def delete(
        self,
        ticket_id: uuid.UUID,
    ) -> None: ...
