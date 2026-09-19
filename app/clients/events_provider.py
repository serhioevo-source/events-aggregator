from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.clients.protocols import EventsProviderProtocol


class EventsProviderError(Exception):
    """Error communicating with Events Provider API."""


class EventsProviderClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    @property
    def headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key}

    def _create_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        )

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        try:
            async with self._create_client() as client:
                response = await client.request(
                    method,
                    url,
                    headers=self.headers,
                    **kwargs,
                )

            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as exc:
            raise EventsProviderError(
                f"Events Provider returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            raise EventsProviderError("Events Provider request failed") from exc

    async def events(
        self,
        changed_at: str,
        url: str | None = None,
    ) -> dict[str, Any]:
        request_url = url or f"{self.base_url}/api/events/"
        params = None if url else {"changed_at": changed_at}

        response = await self._request(
            "GET",
            request_url,
            params=params,
        )
        return response.json()

    async def seats(self, event_id: str) -> list[str]:
        response = await self._request(
            "GET",
            f"{self.base_url}/api/events/{event_id}/seats/",
        )

        return response.json()["seats"]

    async def register(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        response = await self._request(
            "POST",
            f"{self.base_url}/api/events/{event_id}/register/",
            json={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "seat": seat,
            },
        )

        return response.json()["ticket_id"]

    async def unregister(
        self,
        event_id: str,
        ticket_id: str,
    ) -> bool:
        response = await self._request(
            "DELETE",
            f"{self.base_url}/api/events/{event_id}/unregister/",
            json={"ticket_id": ticket_id},
        )

        return bool(response.json()["success"])


class EventsPaginator:
    def __init__(
        self,
        client: EventsProviderProtocol,
        changed_at: str,
    ) -> None:
        self.client = client
        self.changed_at = changed_at

    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        next_url: str | None = None

        while True:
            page = await self.client.events(
                changed_at=self.changed_at,
                url=next_url,
            )

            for event in page.get("results", []):
                yield event

            next_url = page.get("next")
            if not next_url:
                break
