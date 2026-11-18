from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from pakistan_flood_monitor.config import AppMode


ReviewQueueStatus = Literal["draft", "review", "approved"]
REVIEW_QUEUE_PAGE_SIZE = 25
SIMULATION_WATERMARK = "SIMULATED / DEMO DATA — NOT FOR OPERATIONAL DECISIONS"


class ReviewQueueItem(BaseModel):
    event_id: str
    status: ReviewQueueStatus
    corridor_id: str | None = None
    event_class: str | None = None
    detected_at: datetime | None = None
    machine_confidence_pct: float | None = Field(default=None, ge=0, le=100)
    product_label: str | None = None
    watermark: str | None = None


class ReviewQueuePage(BaseModel):
    app_mode: AppMode
    items: list[ReviewQueueItem]
    next_offset: int | None = Field(ge=0)
