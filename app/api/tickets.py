import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.events_provider import (
    EventsProviderClient,
    EventsProviderError,
)
from app.core.config import settings
from app.db.session import get_session
from app.repositories.events import EventRepository
from app.repositories.tickets import TicketRepository
from app.schemas.ticket import (
    TicketCreateRequest,
    TicketCreateResponse,
    TicketDeleteResponse,
)
from app.services.tickets import (
    TicketCancellationError,
    TicketEventNotFoundError,
    TicketEventNotPublishedError,
    TicketNotFoundError,
    TicketService,
)

router = APIRouter(tags=["tickets"])


def create_ticket_service(session: AsyncSession) -> TicketService:
    return TicketService(
        event_repository=EventRepository(session),
        ticket_repository=TicketRepository(session),
        provider_client=EventsProviderClient(
            base_url=settings.events_provider_base_url,
            api_key=settings.events_provider_api_key,
        ),
    )


@router.post(
    "/tickets",
    response_model=TicketCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ticket(
    request: TicketCreateRequest,
) -> TicketCreateResponse:
    async for session in get_session():
        session: AsyncSession
        service = create_ticket_service(session)

        try:
            ticket_id = await service.register(
                event_id=request.event_id,
                first_name=request.first_name,
                last_name=request.last_name,
                email=request.email,
                seat=request.seat,
            )
            await session.commit()
        except TicketEventNotFoundError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=404,
                detail="Event not found",
            ) from exc
        except TicketEventNotPublishedError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=409,
                detail="Event is not published",
            ) from exc
        except EventsProviderError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=502,
                detail="Events Provider ticket registration failed",
            ) from exc
        except Exception:
            await session.rollback()
            raise

        return TicketCreateResponse(ticket_id=ticket_id)

    raise HTTPException(
        status_code=500,
        detail="Database session unavailable",
    )


@router.delete(
    "/tickets/{ticket_id}",
    response_model=TicketDeleteResponse,
)
async def delete_ticket(
    ticket_id: uuid.UUID,
) -> TicketDeleteResponse:
    async for session in get_session():
        session: AsyncSession
        service = create_ticket_service(session)

        try:
            success = await service.cancel(ticket_id)
            await session.commit()
        except TicketNotFoundError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=404,
                detail="Ticket not found",
            ) from exc
        except TicketCancellationError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=502,
                detail="Events Provider did not confirm cancellation",
            ) from exc
        except EventsProviderError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=502,
                detail="Events Provider ticket cancellation failed",
            ) from exc
        except Exception:
            await session.rollback()
            raise

        return TicketDeleteResponse(success=success)

    raise HTTPException(
        status_code=500,
        detail="Database session unavailable",
    )
