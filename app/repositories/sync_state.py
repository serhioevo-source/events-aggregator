from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sync_state import SyncState


class SyncStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self) -> SyncState | None:
        return await self.session.scalar(
            select(SyncState).where(SyncState.id == 1)
        )

    async def save(
        self,
        *,
        last_sync_time: datetime,
        last_changed_at: datetime | None,
        sync_status: str,
    ) -> None:
        state = await self.get()

        if state is None:
            state = SyncState(
                id=1,
                last_sync_time=last_sync_time,
                last_changed_at=last_changed_at,
                sync_status=sync_status,
            )
            self.session.add(state)
            return

        state.last_sync_time = last_sync_time
        state.last_changed_at = last_changed_at
        state.sync_status = sync_status
