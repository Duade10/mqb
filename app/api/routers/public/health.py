from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["Public"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
