from collections.abc import AsyncIterator
from typing import Any

import httpx


class EventsProviderError(Exception):
    """Error returned by Events Provider API."""


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

    async def events(
        self,
        changed_at: str,
        url: str | None = None,
    ) -> dict[str, Any]:
        request_url = url or f"{self.base_url}/api/events/"
        params = None if url else {"changed_at": changed_at}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                request_url,
                params=params,
                headers=self.headers,
            )

        self._raise_for_status(response)
        return response.json()

    async def seats(self, event_id: str) -> list[str]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/api/events/{event_id}/seats/",
                headers=self.headers,
            )

        self._raise_for_status(response)
        data = response.json()
        return data["seats"]

    async def register(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> str:
        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "seat": seat,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/events/{event_id}/register/",
                headers=self.headers,
                json=payload,
            )

        self._raise_for_status(response)
        return response.json()["ticket_id"]

    async def unregister(
        self,
        event_id: str,
        ticket_id: str,
    ) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                "DELETE",
                f"{self.base_url}/api/events/{event_id}/unregister/",
                headers=self.headers,
                json={"ticket_id": ticket_id},
            )

        self._raise_for_status(response)
        return bool(response.json()["success"])

    def _raise_for_status(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise EventsProviderError(
                f"Events Provider returned HTTP {response.status_code}"
            ) from exc


class EventsPaginator:
    def __init__(
        self,
        client: EventsProviderClient,
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
