from fastapi import FastAPI

from app.api.routers import admin, analytics, events, health, monitoring

app = FastAPI(title="Pakistan Flood Monitor")
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
