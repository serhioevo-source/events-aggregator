from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory


router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    async with async_session_factory() as session:
        session: AsyncSession
        await session.execute(text("SELECT 1"))

    return {"status": "ok"}
