from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.clients.events_provider import (
    EventsPaginator,
    EventsProviderClient,
)


@pytest.mark.asyncio
async def test_events_client_sends_changed_at_and_api_key() -> None:
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "next": None,
        "previous": None,
        "results": [],
    }

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)) as get:
        client = EventsProviderClient(
            base_url="http://provider",
            api_key="test-key",
        )

        result = await client.events("2000-01-01")

    assert result["results"] == []

    get.assert_awaited_once_with(
        "http://provider/api/events/",
        params={"changed_at": "2000-01-01"},
        headers={"x-api-key": "test-key"},
    )


@pytest.mark.asyncio
async def test_paginator_iterates_over_all_pages() -> None:
    client = Mock()

    client.events = AsyncMock(
        side_effect=[
            {
                "next": "http://provider/api/events/?cursor=second",
                "previous": None,
                "results": [{"id": "event-1"}],
            },
            {
                "next": None,
                "previous": "http://provider/api/events/?cursor=first",
                "results": [{"id": "event-2"}],
            },
        ]
    )

    paginator = EventsPaginator(
        client=client,
        changed_at="2000-01-01",
    )

    events = [event async for event in paginator]

    assert events == [
        {"id": "event-1"},
        {"id": "event-2"},
    ]

    assert client.events.await_count == 2
    client.events.assert_any_await(
        changed_at="2000-01-01",
        url=None,
    )
    client.events.assert_any_await(
        changed_at="2000-01-01",
        url="http://provider/api/events/?cursor=second",
    )


@pytest.mark.asyncio
async def test_register_returns_ticket_id() -> None:
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {"ticket_id": "ticket-123"}

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=response)):
        client = EventsProviderClient(
            base_url="http://provider",
            api_key="test-key",
        )

        ticket_id = await client.register(
            event_id="event-123",
            first_name="Ivan",
            last_name="Ivanov",
            email="ivan@example.com",
            seat="A15",
        )

    assert ticket_id == "ticket-123"


@pytest.mark.asyncio
async def test_seats_returns_available_seats() -> None:
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "seats": ["A1", "A3", "B1"],
    }

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
        client = EventsProviderClient(
            base_url="http://provider",
            api_key="test-key",
        )

        seats = await client.seats("event-123")

    assert seats == ["A1", "A3", "B1"]
