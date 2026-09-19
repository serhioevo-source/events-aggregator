import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.seats import (
    EventNotFoundError,
    EventNotPublishedError,
    SeatsService,
)


def make_service(
    *,
    event,
    seats: list[str] | None = None,
) -> tuple[SeatsService, Mock]:
    repository = Mock()
    repository.get_by_id = AsyncMock(return_value=event)

    provider = Mock()
    provider.seats = AsyncMock(return_value=seats or ["A1", "A2"])

    service = SeatsService(
        event_repository=repository,
        provider_client=provider,
        cache={},
        cache_ttl_seconds=30,
    )

    return service, provider


@pytest.mark.asyncio
async def test_seats_service_returns_provider_seats() -> None:
    event_id = uuid.uuid4()
    event = Mock(status="published")

    service, provider = make_service(
        event=event,
        seats=["A1", "A3"],
    )

    result = await service.get_available_seats(event_id)

    assert result == ["A1", "A3"]
    provider.seats.assert_awaited_once_with(str(event_id))


@pytest.mark.asyncio
async def test_seats_service_uses_cache() -> None:
    event_id = uuid.uuid4()
    event = Mock(status="published")

    service, provider = make_service(
        event=event,
        seats=["B1", "B2"],
    )

    first = await service.get_available_seats(event_id)
    second = await service.get_available_seats(event_id)

    assert first == ["B1", "B2"]
    assert second == ["B1", "B2"]
    provider.seats.assert_awaited_once()


@pytest.mark.asyncio
async def test_seats_service_rejects_missing_event() -> None:
    event_id = uuid.uuid4()

    service, provider = make_service(event=None)

    with pytest.raises(EventNotFoundError):
        await service.get_available_seats(event_id)

    provider.seats.assert_not_awaited()


@pytest.mark.asyncio
async def test_seats_service_rejects_unpublished_event() -> None:
    event_id = uuid.uuid4()
    event = Mock(status="finished")

    service, provider = make_service(event=event)

    with pytest.raises(EventNotPublishedError):
        await service.get_available_seats(event_id)

    provider.seats.assert_not_awaited()


@pytest.mark.asyncio
async def test_seats_service_refreshes_expired_cache() -> None:
    import time

    from app.services.seats import SeatsCacheEntry

    event_id = uuid.uuid4()
    event = Mock(status="published")

    service, provider = make_service(
        event=event,
        seats=["C1", "C2"],
    )

    service.cache[event_id] = SeatsCacheEntry(
        seats=["OLD"],
        expires_at=time.monotonic() - 1,
    )

    result = await service.get_available_seats(event_id)

    assert result == ["C1", "C2"]
    provider.seats.assert_awaited_once_with(str(event_id))
