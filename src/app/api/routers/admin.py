from fastapi import APIRouter

from app.pipelines import publish_events_pipeline

router = APIRouter()


@router.post("/publish")
def publish_events() -> dict[str, str]:
    return {"run": publish_events_pipeline()}
