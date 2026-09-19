import math
import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, HTTPException, Query, Request

from app.clients.events_provider import EventsProviderClient, EventsProviderError
from app.core.config import settings
from app.db.session import get_session
from app.repositories.events import EventRepository
from app.schemas.event import (
    EventResponse,
    EventSeatsResponse,
    EventsListResponse,
    PlaceResponse,
)
from app.services.seats import (
    EventNotFoundError,
    EventNotPublishedError,
    SeatsCacheEntry,
    SeatsService,
)
from app.services.sync_runner import run_events_sync

router = APIRouter(tags=["events"])

seats_cache: dict[uuid.UUID, SeatsCacheEntry] = {}


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
    try:
        count = await run_events_sync()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Events Provider synchronization failed",
        ) from exc

    return {
        "status": "ok",
        "synced": count,
    }


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


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: uuid.UUID) -> EventResponse:
    async for session in get_session():
        repository = EventRepository(session)

        event = await repository.get_by_id(event_id)

        if event is None:
            raise HTTPException(
                status_code=404,
                detail="Event not found",
            )

        return event_to_response(event)

    raise HTTPException(
        status_code=500,
        detail="Database session unavailable",
    )


@router.get(
    "/events/{event_id}/seats",
    response_model=EventSeatsResponse,
)
async def get_event_seats(event_id: uuid.UUID) -> EventSeatsResponse:
    async for session in get_session():
        repository = EventRepository(session)

        provider_client = EventsProviderClient(
            base_url=settings.events_provider_base_url,
            api_key=settings.events_provider_api_key,
        )

        service = SeatsService(
            event_repository=repository,
            provider_client=provider_client,
            cache=seats_cache,
            cache_ttl_seconds=settings.seats_cache_ttl_seconds,
        )

        try:
            seats = await service.get_available_seats(event_id)
        except EventNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail="Event not found",
            ) from exc
        except EventNotPublishedError as exc:
            raise HTTPException(
                status_code=409,
                detail="Event is not published",
            ) from exc
        except EventsProviderError as exc:
            raise HTTPException(
                status_code=502,
                detail="Events Provider request failed",
            ) from exc

        return EventSeatsResponse(
            event_id=event_id,
            available_seats=seats,
        )

    raise HTTPException(
        status_code=500,
        detail="Database session unavailable",
    )
