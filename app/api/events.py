import math
from datetime import UTC, date, datetime

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.events_provider import EventsProviderClient
from app.core.config import settings
from app.db.session import get_session
from app.repositories.events import EventRepository
from app.repositories.sync_state import SyncStateRepository
from app.schemas.event import (
    EventResponse,
    EventsListResponse,
    PlaceResponse,
)
from app.services.sync import SyncEventsService

router = APIRouter(tags=["events"])


def event_to_response(event) -> EventResponse:
    return EventResponse(
        id=event.id,
        name=event.name,
        place=PlaceResponse(
            id=event.place_id,
            name=event.place_name,
            city=event.place_city,
            address=event.place_address,
            seats_pattern=event.seats_pattern,
        ),
        event_time=event.event_time,
        registration_deadline=event.registration_deadline,
        status=event.status,
        number_of_visitors=event.number_of_visitors,
    )


@router.post("/sync/trigger")
async def trigger_sync() -> dict[str, int | str]:
    async for session in get_session():
        session: AsyncSession

        event_repository = EventRepository(session)
        sync_state_repository = SyncStateRepository(session)

        provider_client = EventsProviderClient(
            base_url=settings.events_provider_base_url,
            api_key=settings.events_provider_api_key,
        )

        service = SyncEventsService(
            event_repository=event_repository,
            sync_state_repository=sync_state_repository,
            provider_client=provider_client,
        )

        try:
            count = await service.sync()
            await session.commit()
        except Exception as exc:
            await session.rollback()
            raise HTTPException(
                status_code=502,
                detail="Events Provider synchronization failed",
            ) from exc

        return {
            "status": "ok",
            "synced": count,
        }

    raise HTTPException(status_code=500, detail="Database session unavailable")


@router.get("/events", response_model=EventsListResponse)
async def list_events(
    request: Request,
    date_from: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1),
) -> EventsListResponse:
    async for session in get_session():
        repository = EventRepository(session)

        date_from_datetime = (
            datetime.combine(date_from, datetime.min.time(), tzinfo=UTC)
            if date_from is not None
            else None
        )

        offset = (page - 1) * page_size

        events, count = await repository.list_events(
            date_from=date_from_datetime,
            offset=offset,
            limit=page_size,
        )

        pages = math.ceil(count / page_size) if count else 0

        next_url = None
        previous_url = None

        if page < pages:
            next_url = str(
                request.url.include_query_params(
                    page=page + 1,
                    page_size=page_size,
                )
            )

        if page > 1:
            previous_url = str(
                request.url.include_query_params(
                    page=page - 1,
                    page_size=page_size,
                )
            )

        return EventsListResponse(
            count=count,
            next=next_url,
            previous=previous_url,
            results=[event_to_response(event) for event in events],
        )

    raise HTTPException(status_code=500, detail="Database session unavailable")
