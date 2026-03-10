from datetime import datetime

from pydantic import BaseModel


class SceneDiscoveryRequest(BaseModel):
    corridor_id: str
    start_time: datetime
    end_time: datetime


class CorridorStatusResponse(BaseModel):
    corridor_id: str
    latest_scene_id: str | None
    latest_status: str
