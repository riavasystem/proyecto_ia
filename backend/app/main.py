import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import DomainError, domain_error_handler
from app.core.logging import configure_logging, get_logger
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.tenant import TenantContextMiddleware
from app.services import webhook_queue

settings = get_settings()
configure_logging(debug=settings.debug)
logger = get_logger(service="main")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    await webhook_queue.requeue_pending()
    stop_event = asyncio.Event()
    worker_task = asyncio.create_task(webhook_queue.run_worker(stop_event))
    try:
        yield
    finally:
        stop_event.set()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        logger.info("webhook_worker_stopped")


app = FastAPI(
    title="Proyecto IA - Core API",
    version="1.0.0",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(TenantContextMiddleware)
app.add_middleware(RequestIDMiddleware)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_exception_handler(DomainError, domain_error_handler)

app.include_router(api_router, prefix=settings.api_v1_prefix)
