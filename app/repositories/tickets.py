import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket


class TicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        ticket_id: uuid.UUID,
        event_id: uuid.UUID,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> Ticket:
        ticket = Ticket(
            id=ticket_id,
            event_id=event_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            seat=seat,
        )

        self.session.add(ticket)
        await self.session.flush()

        return ticket

    async def get_by_id(self, ticket_id: uuid.UUID) -> Ticket | None:
        return await self.session.scalar(select(Ticket).where(Ticket.id == ticket_id))

    async def delete(self, ticket_id: uuid.UUID) -> None:
        await self.session.execute(delete(Ticket).where(Ticket.id == ticket_id))
