import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.tickets import (
    TicketCancellationError,
    TicketEventNotFoundError,
    TicketEventNotPublishedError,
    TicketNotFoundError,
    TicketService,
)


def make_service(
    *,
    event=None,
    ticket=None,
    provider_ticket_id: str | None = None,
    unregister_success: bool = True,
) -> tuple[TicketService, Mock, Mock, Mock]:
    event_repository = Mock()
    event_repository.get_by_id = AsyncMock(return_value=event)

    ticket_repository = Mock()
    ticket_repository.create = AsyncMock()
    ticket_repository.get_by_id = AsyncMock(return_value=ticket)
    ticket_repository.delete = AsyncMock()

    provider = Mock()
    provider.register = AsyncMock(return_value=provider_ticket_id)
    provider.unregister = AsyncMock(return_value=unregister_success)

    service = TicketService(
        event_repository=event_repository,
        ticket_repository=ticket_repository,
        provider_client=provider,
    )

    return service, event_repository, ticket_repository, provider


@pytest.mark.asyncio
async def test_register_ticket_saves_provider_ticket() -> None:
    event_id = uuid.uuid4()
    ticket_id = uuid.uuid4()
    event = Mock(status="published")

    service, _, repository, provider = make_service(
        event=event,
        provider_ticket_id=str(ticket_id),
    )

    result = await service.register(
        event_id=event_id,
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A15",
    )

    assert result == ticket_id

    provider.register.assert_awaited_once_with(
        event_id=str(event_id),
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A15",
    )

    repository.create.assert_awaited_once_with(
        ticket_id=ticket_id,
        event_id=event_id,
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A15",
    )


@pytest.mark.asyncio
async def test_register_ticket_rejects_missing_event() -> None:
    event_id = uuid.uuid4()

    service, _, repository, provider = make_service(event=None)

    with pytest.raises(TicketEventNotFoundError):
        await service.register(
            event_id=event_id,
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="A15",
        )

    provider.register.assert_not_awaited()
    repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_ticket_rejects_unpublished_event() -> None:
    event_id = uuid.uuid4()
    event = Mock(status="finished")

    service, _, repository, provider = make_service(event=event)

    with pytest.raises(TicketEventNotPublishedError):
        await service.register(
            event_id=event_id,
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="A15",
        )

    provider.register.assert_not_awaited()
    repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancel_ticket_unregisters_and_deletes_ticket() -> None:
    ticket_id = uuid.uuid4()
    event_id = uuid.uuid4()

    ticket = Mock(
        id=ticket_id,
        event_id=event_id,
    )

    service, _, repository, provider = make_service(
        ticket=ticket,
        unregister_success=True,
    )

    result = await service.cancel(ticket_id)

    assert result is True

    provider.unregister.assert_awaited_once_with(
        event_id=str(event_id),
        ticket_id=str(ticket_id),
    )
    repository.delete.assert_awaited_once_with(ticket_id)


@pytest.mark.asyncio
async def test_cancel_ticket_rejects_missing_ticket() -> None:
    ticket_id = uuid.uuid4()

    service, _, repository, provider = make_service(ticket=None)

    with pytest.raises(TicketNotFoundError):
        await service.cancel(ticket_id)

    provider.unregister.assert_not_awaited()
    repository.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_cancel_ticket_keeps_ticket_when_provider_rejects() -> None:
    ticket_id = uuid.uuid4()
    event_id = uuid.uuid4()

    ticket = Mock(
        id=ticket_id,
        event_id=event_id,
    )

    service, _, repository, provider = make_service(
        ticket=ticket,
        unregister_success=False,
    )

    with pytest.raises(TicketCancellationError):
        await service.cancel(ticket_id)

    provider.unregister.assert_awaited_once()
    repository.delete.assert_not_awaited()
