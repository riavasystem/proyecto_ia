from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from app.core.redis import get_redis

TokenType = Literal["access", "refresh"]


def _key(company_id: UUID, token_type: TokenType, jti: str) -> str:
    return f"tenant:{company_id}:revoked_{token_type}:{jti}"


async def revoke_token(
    company_id: UUID, token_type: TokenType, jti: str, expires_at: datetime
) -> None:
    """Guarda el jti en Redis hasta que el token hubiera expirado de todas
    formas — no tiene sentido recordarlo más allá de eso."""
    ttl_seconds = int((expires_at - datetime.now(UTC)).total_seconds())
    if ttl_seconds <= 0:
        return
    await get_redis().set(_key(company_id, token_type, jti), "1", ex=ttl_seconds)


async def is_token_revoked(company_id: UUID, token_type: TokenType, jti: str) -> bool:
    return await get_redis().exists(_key(company_id, token_type, jti)) > 0


async def revoke_refresh_token(company_id: UUID, jti: str, expires_at: datetime) -> None:
    await revoke_token(company_id, "refresh", jti, expires_at)


async def is_refresh_token_revoked(company_id: UUID, jti: str) -> bool:
    return await is_token_revoked(company_id, "refresh", jti)


async def revoke_access_token(company_id: UUID, jti: str, expires_at: datetime) -> None:
    await revoke_token(company_id, "access", jti, expires_at)


async def is_access_token_revoked(company_id: UUID, jti: str) -> bool:
    return await is_token_revoked(company_id, "access", jti)
