import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, event_data: dict) -> None:
        place = event_data["place"]

        values = {
            "id": uuid.UUID(event_data["id"]),
            "name": event_data["name"],
            "place_id": uuid.UUID(place["id"]) if place.get("id") else None,
            "place_name": place.get("name"),
            "place_city": place.get("city"),
            "place_address": place.get("address"),
            "seats_pattern": place.get("seats_pattern"),
            "event_time": datetime.fromisoformat(event_data["event_time"]),
            "registration_deadline": (
                datetime.fromisoformat(event_data["registration_deadline"])
                if event_data.get("registration_deadline")
                else None
            ),
            "status": event_data["status"],
            "number_of_visitors": event_data.get("number_of_visitors", 0),
            "changed_at": datetime.fromisoformat(event_data["changed_at"]),
            "created_at": datetime.fromisoformat(event_data["created_at"]),
            "status_changed_at": (
                datetime.fromisoformat(event_data["status_changed_at"])
                if event_data.get("status_changed_at")
                else None
            ),
        }

        statement = insert(Event).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[Event.id],
            set_={
                key: value
                for key, value in values.items()
                if key != "id"
            },
        )

        await self.session.execute(statement)

    async def list_events(
        self,
        date_from: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Event], int]:
        conditions = []

        if date_from is not None:
            conditions.append(Event.event_time >= date_from)

        count_statement = select(func.count()).select_from(Event)
        events_statement = (
            select(Event)
            .order_by(Event.event_time, Event.id)
            .offset(offset)
            .limit(limit)
        )

        if conditions:
            count_statement = count_statement.where(*conditions)
            events_statement = events_statement.where(*conditions)

        count = await self.session.scalar(count_statement)
        result = await self.session.scalars(events_statement)

        return list(result), int(count or 0)
