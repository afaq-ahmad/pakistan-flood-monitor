from __future__ import annotations

import warnings

from fastapi import FastAPI

from app.api.routers import admin, analytics, events, health, monitoring

warnings.warn(
    "Deprecated runtime entrypoint: 'app.api.main:app' is prototype-only and will be removed after 2026-12-31. "
    "Use 'pakistan_flood_monitor.api.main:app' for all runtime integrations.",
    DeprecationWarning,
    stacklevel=1,
)

app = FastAPI(title="Pakistan Flood Monitor")
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
