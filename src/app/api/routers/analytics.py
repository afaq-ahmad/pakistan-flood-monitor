from fastapi import APIRouter

router = APIRouter()


@router.get("/summary")
def analytics_summary() -> dict[str, int]:
    return {"active_events": 0}
