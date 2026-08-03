from fastapi import APIRouter

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/health")
async def public_health() -> dict[str, str]:
    return {"status": "ok"}
