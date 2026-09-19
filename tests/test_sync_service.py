from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.sync import INITIAL_CHANGED_AT, SyncEventsService


def make_event(
    *,
    event_id: str,
    changed_at: str,
) -> dict:
    return {
        "id": event_id,
        "changed_at": changed_at,
    }


@pytest.mark.asyncio
async def test_initial_sync_uses_initial_changed_at() -> None:
    event_repository = Mock()
    event_repository.upsert = AsyncMock()

    sync_repository = Mock()
    sync_repository.get = AsyncMock(return_value=None)
    sync_repository.save = AsyncMock()

    provider = Mock()
    provider.events = AsyncMock(
        return_value={
            "results": [],
            "next": None,
        }
    )

    service = SyncEventsService(
        event_repository=event_repository,
        sync_state_repository=sync_repository,
        provider_client=provider,
    )

    result = await service.sync()

    assert result == 0
    provider.events.assert_awaited_once_with(
        changed_at=INITIAL_CHANGED_AT,
        url=None,
    )

    saved = sync_repository.save.await_args.kwargs
    assert saved["sync_status"] == "success"
    assert saved["last_changed_at"] is None


@pytest.mark.asyncio
async def test_incremental_sync_uses_last_changed_date() -> None:
    previous = datetime(
        2026,
        1,
        5,
        15,
        30,
        tzinfo=UTC,
    )

    event_repository = Mock()
    event_repository.upsert = AsyncMock()

    state = Mock(last_changed_at=previous)

    sync_repository = Mock()
    sync_repository.get = AsyncMock(return_value=state)
    sync_repository.save = AsyncMock()

    provider = Mock()
    provider.events = AsyncMock(
        return_value={
            "results": [
                make_event(
                    event_id="event-1",
                    changed_at="2026-01-06T12:00:00+00:00",
                )
            ],
            "next": None,
        }
    )

    service = SyncEventsService(
        event_repository=event_repository,
        sync_state_repository=sync_repository,
        provider_client=provider,
    )

    result = await service.sync()

    assert result == 1

    provider.events.assert_awaited_once_with(
        changed_at="2026-01-05",
        url=None,
    )

    event_repository.upsert.assert_awaited_once()

    saved = sync_repository.save.await_args.kwargs
    assert saved["sync_status"] == "success"
    assert saved["last_changed_at"] == datetime(
        2026,
        1,
        6,
        12,
        0,
        tzinfo=UTC,
    )
