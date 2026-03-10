from datetime import datetime

from pydantic import BaseModel


class EventCreateRequest(BaseModel):
    corridor_id: str
    event_type: str
    confidence: float


class EventResponse(BaseModel):
    id: int
    corridor_id: str
    event_type: str
    confidence: float
    review_status: str
    created_at: datetime
