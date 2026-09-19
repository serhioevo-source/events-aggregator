import asyncio
from unittest.mock import AsyncMock

import pytest

from app.workers import events_sync


@pytest.mark.asyncio
async def test_worker_runs_sync_after_interval(
    monkeypatch,
) -> None:
    sync = AsyncMock()

    sleep_calls = 0

    async def fake_sleep(seconds: int) -> None:
        nonlocal sleep_calls
        sleep_calls += 1

        assert seconds == 86400

        if sleep_calls > 1:
            raise asyncio.CancelledError

    monkeypatch.setattr(
        events_sync.settings,
        "sync_interval_seconds",
        86400,
    )
    monkeypatch.setattr(
        events_sync.asyncio,
        "sleep",
        fake_sleep,
    )
    monkeypatch.setattr(
        events_sync,
        "run_events_sync",
        sync,
    )

    with pytest.raises(asyncio.CancelledError):
        await events_sync.run_events_sync_worker()

    sync.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_survives_sync_failure(
    monkeypatch,
) -> None:
    sync = AsyncMock(
        side_effect=[
            RuntimeError("provider failed"),
            None,
        ]
    )

    sleep_calls = 0

    async def fake_sleep(seconds: int) -> None:
        nonlocal sleep_calls
        sleep_calls += 1

        if sleep_calls > 2:
            raise asyncio.CancelledError

    monkeypatch.setattr(
        events_sync.asyncio,
        "sleep",
        fake_sleep,
    )
    monkeypatch.setattr(
        events_sync,
        "run_events_sync",
        sync,
    )

    with pytest.raises(asyncio.CancelledError):
        await events_sync.run_events_sync_worker()

    assert sync.await_count == 2


@pytest.mark.asyncio
async def test_worker_propagates_cancellation(
    monkeypatch,
) -> None:
    async def cancelled_sleep(seconds: int) -> None:
        raise asyncio.CancelledError

    sync = AsyncMock()

    monkeypatch.setattr(
        events_sync.asyncio,
        "sleep",
        cancelled_sleep,
    )
    monkeypatch.setattr(
        events_sync,
        "run_events_sync",
        sync,
    )

    with pytest.raises(asyncio.CancelledError):
        await events_sync.run_events_sync_worker()

    sync.assert_not_awaited()
