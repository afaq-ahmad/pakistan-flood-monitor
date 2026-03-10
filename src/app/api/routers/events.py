from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_events() -> list[dict[str, str]]:
    return []
