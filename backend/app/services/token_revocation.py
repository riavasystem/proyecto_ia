from datetime import UTC, datetime
from uuid import UUID

from app.core.redis import get_redis


def _key(company_id: UUID, jti: str) -> str:
    return f"tenant:{company_id}:revoked_refresh:{jti}"


async def revoke_refresh_token(company_id: UUID, jti: str, expires_at: datetime) -> None:
    """Guarda el jti en Redis hasta que el token hubiera expirado de todas
    formas — no tiene sentido recordarlo más allá de eso."""
    ttl_seconds = int((expires_at - datetime.now(UTC)).total_seconds())
    if ttl_seconds <= 0:
        return
    await get_redis().set(_key(company_id, jti), "1", ex=ttl_seconds)


async def is_refresh_token_revoked(company_id: UUID, jti: str) -> bool:
    return await get_redis().exists(_key(company_id, jti)) > 0
