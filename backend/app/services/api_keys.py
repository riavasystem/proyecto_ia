from datetime import UTC, datetime

from sqlalchemy import select

from app.core.security import hash_api_key
from app.db import session as db_session
from app.models.api_key import ApiKey


async def resolve_api_key(token: str) -> ApiKey | None:
    """Busca la API key por hash, valida que esté activa y no expirada, y
    actualiza last_used_at. Usa su propia sesión porque corre en middleware,
    antes de que exista la sesión de request inyectada por dependencia.

    Se accede a `db_session.async_session_factory` como atributo de módulo
    (no importado por nombre) para que los tests puedan reemplazarlo por uno
    apuntando a la base de datos de prueba."""
    key_hash = hash_api_key(token)
    async with db_session.async_session_factory() as session:
        result = await session.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
        api_key = result.scalar_one_or_none()
        if api_key is None or not api_key.is_active:
            return None
        if api_key.expires_at is not None and api_key.expires_at < datetime.now(UTC):
            return None
        api_key.last_used_at = datetime.now(UTC)
        await session.commit()
        return api_key
