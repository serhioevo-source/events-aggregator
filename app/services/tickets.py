import uuid

from app.clients.protocols import EventsProviderProtocol
from app.repositories.protocols import (
    EventRepositoryProtocol,
    TicketRepositoryProtocol,
)


class TicketEventNotFoundError(Exception):
    """Ticket registration event does not exist locally."""


class TicketEventNotPublishedError(Exception):
    """Tickets can only be registered for published events."""


class TicketNotFoundError(Exception):
    """Requested ticket does not exist locally."""


class TicketCancellationError(Exception):
    """Events Provider did not confirm ticket cancellation."""


class TicketService:
    def __init__(
        self,
        event_repository: EventRepositoryProtocol,
        ticket_repository: TicketRepositoryProtocol,
        provider_client: EventsProviderProtocol,
    ) -> None:
        self.event_repository = event_repository
        self.ticket_repository = ticket_repository
        self.provider_client = provider_client

    async def register(
        self,
        *,
        event_id: uuid.UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> uuid.UUID:
        event = await self.event_repository.get_by_id(event_id)

        if event is None:
            raise TicketEventNotFoundError

        if event.status != "published":
            raise TicketEventNotPublishedError

        provider_ticket_id = await self.provider_client.register(
            event_id=str(event_id),
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )

        ticket_id = uuid.UUID(provider_ticket_id)

        await self.ticket_repository.create(
            ticket_id=ticket_id,
            event_id=event_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )

        return ticket_id

    async def cancel(self, ticket_id: uuid.UUID) -> bool:
        ticket = await self.ticket_repository.get_by_id(ticket_id)

        if ticket is None:
            raise TicketNotFoundError

        success = await self.provider_client.unregister(
            event_id=str(ticket.event_id),
            ticket_id=str(ticket.id),
        )

        if not success:
            raise TicketCancellationError

        await self.ticket_repository.delete(ticket_id)

        return True
