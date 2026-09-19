import uuid
from datetime import datetime

from pydantic import BaseModel


class PlaceResponse(BaseModel):
    id: uuid.UUID | None
    name: str | None
    city: str | None
    address: str | None
    seats_pattern: str | None = None


class EventResponse(BaseModel):
    id: uuid.UUID
    name: str
    place: PlaceResponse
    event_time: datetime
    registration_deadline: datetime | None
    status: str
    number_of_visitors: int


class EventsListResponse(BaseModel):
    count: int
    next: str | None
    previous: str | None
    results: list[EventResponse]
