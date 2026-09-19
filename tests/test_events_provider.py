from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.clients.events_provider import (
    EventsPaginator,
    EventsProviderClient,
    EventsProviderError,
)


def make_http_client(response: Mock) -> AsyncMock:
    http_client = AsyncMock()
    http_client.__aenter__.return_value = http_client
    http_client.__aexit__.return_value = None
    http_client.request.return_value = response
    return http_client


@pytest.mark.asyncio
async def test_events_client_sends_changed_at_and_api_key(
    monkeypatch,
) -> None:
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "next": None,
        "previous": None,
        "results": [],
    }

    http_client = make_http_client(response)

    client = EventsProviderClient(
        base_url="http://provider",
        api_key="test-key",
    )

    monkeypatch.setattr(
        client,
        "_create_client",
        lambda: http_client,
    )

    result = await client.events("2000-01-01")

    assert result["results"] == []

    http_client.request.assert_awaited_once_with(
        "GET",
        "http://provider/api/events/",
        headers={"x-api-key": "test-key"},
        params={"changed_at": "2000-01-01"},
    )


@pytest.mark.asyncio
async def test_paginator_iterates_all_pages() -> None:
    client = Mock()

    client.events = AsyncMock(
        side_effect=[
            {
                "results": [{"id": "event-1"}],
                "next": "http://provider/api/events/?cursor=next",
            },
            {
                "results": [{"id": "event-2"}],
                "next": None,
            },
        ]
    )

    paginator = EventsPaginator(
        client=client,
        changed_at="2000-01-01",
    )

    result = [event async for event in paginator]

    assert result == [
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
        url="http://provider/api/events/?cursor=next",
    )


@pytest.mark.asyncio
async def test_register_returns_ticket_id(monkeypatch) -> None:
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "ticket_id": "ticket-123",
    }

    http_client = make_http_client(response)

    client = EventsProviderClient(
        base_url="http://provider",
        api_key="test-key",
    )

    monkeypatch.setattr(
        client,
        "_create_client",
        lambda: http_client,
    )

    ticket_id = await client.register(
        event_id="event-123",
        first_name="Ivan",
        last_name="Ivanov",
        email="ivan@example.com",
        seat="A15",
    )

    assert ticket_id == "ticket-123"

    http_client.request.assert_awaited_once_with(
        "POST",
        "http://provider/api/events/event-123/register/",
        headers={"x-api-key": "test-key"},
        json={
            "first_name": "Ivan",
            "last_name": "Ivanov",
            "email": "ivan@example.com",
            "seat": "A15",
        },
    )


@pytest.mark.asyncio
async def test_seats_returns_available_seats(monkeypatch) -> None:
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "seats": ["A1", "A3", "B1"],
    }

    http_client = make_http_client(response)

    client = EventsProviderClient(
        base_url="http://provider",
        api_key="test-key",
    )

    monkeypatch.setattr(
        client,
        "_create_client",
        lambda: http_client,
    )

    seats = await client.seats("event-123")

    assert seats == ["A1", "A3", "B1"]

    http_client.request.assert_awaited_once_with(
        "GET",
        "http://provider/api/events/event-123/seats/",
        headers={"x-api-key": "test-key"},
    )


@pytest.mark.asyncio
async def test_unregister_returns_success(monkeypatch) -> None:
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "success": True,
    }

    http_client = make_http_client(response)

    client = EventsProviderClient(
        base_url="http://provider",
        api_key="test-key",
    )

    monkeypatch.setattr(
        client,
        "_create_client",
        lambda: http_client,
    )

    result = await client.unregister(
        event_id="event-123",
        ticket_id="ticket-123",
    )

    assert result is True

    http_client.request.assert_awaited_once_with(
        "DELETE",
        "http://provider/api/events/event-123/unregister/",
        headers={"x-api-key": "test-key"},
        json={"ticket_id": "ticket-123"},
    )


@pytest.mark.asyncio
async def test_provider_wraps_transport_error(monkeypatch) -> None:
    client = EventsProviderClient(
        base_url="https://provider.example",
        api_key="test-key",
    )

    request = httpx.Request(
        "GET",
        "https://provider.example/api/events/",
    )

    http_client = AsyncMock()
    http_client.__aenter__.return_value = http_client
    http_client.__aexit__.return_value = None
    http_client.request.side_effect = httpx.ConnectTimeout(
        "connection timed out",
        request=request,
    )

    monkeypatch.setattr(
        client,
        "_create_client",
        lambda: http_client,
    )

    with pytest.raises(
        EventsProviderError,
        match="Events Provider request failed",
    ):
        await client.events("2000-01-01")


@pytest.mark.asyncio
async def test_provider_wraps_http_error(monkeypatch) -> None:
    request = httpx.Request(
        "GET",
        "https://provider.example/api/events/",
    )
    response = httpx.Response(
        500,
        request=request,
    )

    http_client = AsyncMock()
    http_client.__aenter__.return_value = http_client
    http_client.__aexit__.return_value = None
    http_client.request.return_value = response

    client = EventsProviderClient(
        base_url="https://provider.example",
        api_key="test-key",
    )

    monkeypatch.setattr(
        client,
        "_create_client",
        lambda: http_client,
    )

    with pytest.raises(
        EventsProviderError,
        match="Events Provider returned HTTP 500",
    ):
        await client.events("2000-01-01")
