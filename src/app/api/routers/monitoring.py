from fastapi import APIRouter

from app.pipelines import discover_scenes_pipeline

router = APIRouter()


@router.post("/discover-scenes")
def discover_scenes() -> dict[str, str]:
    return {"run": discover_scenes_pipeline()}
