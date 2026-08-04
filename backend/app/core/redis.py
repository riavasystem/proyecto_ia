from redis.asyncio import Redis

from app.core.config import get_settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


async def reset_redis() -> None:
    """Solo para tests: cada test de pytest-asyncio corre en su propio event
    loop, y un cliente creado en un loop anterior queda inválido en el
    siguiente ("Event loop is closed"). Se cierra y se descarta el singleton
    para que el próximo get_redis() cree uno nuevo atado al loop vigente."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
