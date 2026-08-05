import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.rate_limit import enforce_rate_limit
from app.core.redis import get_redis, reset_redis
from app.db import session as db_session
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services import webhook_queue


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient]:
    reset_redis()
    await get_redis().delete(webhook_queue.READY_KEY, webhook_queue.SCHEDULED_KEY)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db() -> AsyncGenerator:  # type: ignore[no-untyped-def]
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[enforce_rate_limit] = lambda: None

    # El middleware de tenant resuelve API keys con su propia sesión (no pasa
    # por Depends), así que hay que apuntar la misma factory ahí también.
    original_session_factory = db_session.async_session_factory
    db_session.async_session_factory = session_factory

    # ASGITransport no dispara eventos de lifespan, así que el worker de la
    # cola de webhooks (normalmente levantado en app.main.lifespan) se arranca
    # y para acá a mano, apuntando a la misma factory de sesiones de test.
    stop_event = asyncio.Event()
    worker_task = asyncio.create_task(webhook_queue.run_worker(stop_event))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    stop_event.set()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

    db_session.async_session_factory = original_session_factory
    app.dependency_overrides.clear()
    await engine.dispose()
