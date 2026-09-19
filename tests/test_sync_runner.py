from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.services import sync_runner


class SessionContext:
    def __init__(self, session) -> None:
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(
        self,
        exc_type,
        exc,
        traceback,
    ) -> None:
        return None


@pytest.mark.asyncio
async def test_sync_runner_commits_success(
    monkeypatch,
) -> None:
    session = Mock()
    session.commit = AsyncMock()

    session_factory = Mock(return_value=SessionContext(session))

    state_repository = Mock()
    state_repository.get = AsyncMock(return_value=None)

    service = Mock()
    service.sync = AsyncMock(return_value=7)

    monkeypatch.setattr(
        sync_runner,
        "async_session_factory",
        session_factory,
    )
    monkeypatch.setattr(
        sync_runner,
        "SyncStateRepository",
        Mock(return_value=state_repository),
    )
    monkeypatch.setattr(
        sync_runner,
        "EventRepository",
        Mock(),
    )
    monkeypatch.setattr(
        sync_runner,
        "EventsProviderClient",
        Mock(),
    )
    monkeypatch.setattr(
        sync_runner,
        "SyncEventsService",
        Mock(return_value=service),
    )

    result = await sync_runner.run_events_sync()

    assert result == 7
    service.sync.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_runner_persists_failed_state(
    monkeypatch,
) -> None:
    previous_changed_at = datetime(
        2026,
        1,
        5,
        12,
        30,
        tzinfo=UTC,
    )

    sync_session = Mock()
    sync_session.commit = AsyncMock()

    failed_session = Mock()
    failed_session.commit = AsyncMock()

    sessions = iter(
        [
            SessionContext(sync_session),
            SessionContext(failed_session),
        ]
    )

    def session_factory():
        return next(sessions)

    current_state = Mock(last_changed_at=previous_changed_at)

    current_repository = Mock()
    current_repository.get = AsyncMock(return_value=current_state)

    failed_repository = Mock()
    failed_repository.save = AsyncMock()

    repositories = iter(
        [
            current_repository,
            failed_repository,
        ]
    )

    def repository_factory(session):
        return next(repositories)

    service = Mock()
    service.sync = AsyncMock(side_effect=RuntimeError("provider failed"))

    monkeypatch.setattr(
        sync_runner,
        "async_session_factory",
        session_factory,
    )
    monkeypatch.setattr(
        sync_runner,
        "SyncStateRepository",
        repository_factory,
    )
    monkeypatch.setattr(
        sync_runner,
        "EventRepository",
        Mock(),
    )
    monkeypatch.setattr(
        sync_runner,
        "EventsProviderClient",
        Mock(),
    )
    monkeypatch.setattr(
        sync_runner,
        "SyncEventsService",
        Mock(return_value=service),
    )

    with pytest.raises(
        RuntimeError,
        match="provider failed",
    ):
        await sync_runner.run_events_sync()

    sync_session.commit.assert_not_awaited()

    failed_repository.save.assert_awaited_once()

    saved = failed_repository.save.await_args.kwargs

    assert saved["sync_status"] == "failed"
    assert saved["last_changed_at"] == previous_changed_at

    failed_session.commit.assert_awaited_once()
