import time

from fastapi import Request, Response

from app.api.deps import CurrentApiKey
from app.core.exceptions import RateLimitExceededError
from app.core.redis import get_redis

WINDOW_SECONDS = 60


async def enforce_rate_limit(request: Request, response: Response, api_key: CurrentApiKey) -> None:
    """Ventana fija de 60s por API key, en Redis. Las requests admin (JWT, sin
    api_key) no pasan por acá. Deja siempre los headers X-RateLimit-* en la
    respuesta, incluso cuando no se excede el límite (sección 10.7 del CLAUDE.md)."""
    if api_key is None:
        return

    redis = get_redis()
    now = int(time.time())
    window_start = now - (now % WINDOW_SECONDS)
    reset_at = window_start + WINDOW_SECONDS
    key = f"tenant:{api_key.company_id}:ratelimit:{api_key.id}:{window_start}"

    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, WINDOW_SECONDS)

    limit = api_key.rate_limit_per_minute
    remaining = max(limit - count, 0)

    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_at)

    if count > limit:
        raise RateLimitExceededError(
            "Rate limit excedido",
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_at),
                "Retry-After": str(reset_at - now),
            },
        )
