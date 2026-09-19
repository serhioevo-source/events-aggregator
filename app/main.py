from fastapi import FastAPI

from app.api.events import router as events_router
from app.api.health import router as health_router

app = FastAPI(
    title="Events Aggregator",
    version="0.1.0",
)

app.include_router(health_router, prefix="/api")
app.include_router(events_router, prefix="/api")
