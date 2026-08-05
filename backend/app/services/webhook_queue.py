import asyncio
import json
import time
from uuid import UUID

from sqlalchemy import select

import app.db.session as db_session
import app.services.webhooks as webhooks
from app.core.logging import get_logger
from app.core.redis import get_redis
from app.models.webhook import WebhookDelivery, WebhookEndpoint

logger = get_logger(service="webhook_queue")

READY_KEY = "webhooks:queue:ready"
SCHEDULED_KEY = "webhooks:queue:scheduled"

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (2.0, 10.0, 30.0)
DELIVERY_TIMEOUT_SECONDS = 5.0
POLL_TIMEOUT_SECONDS = 1


async def enqueue(delivery_id: UUID) -> None:
    """Encola una entrega para que el worker la procese. A diferencia de un
    BackgroundTask en proceso, esto sobrevive a un reinicio del backend: el
    id queda en Redis hasta que el worker lo consume."""
    await get_redis().rpush(READY_KEY, str(delivery_id))


async def _schedule_retry(delivery_id: UUID, delay_seconds: float) -> None:
    await get_redis().zadd(SCHEDULED_KEY, {str(delivery_id): time.time() + delay_seconds})


async def _promote_due_retries() -> None:
    redis = get_redis()
    now = time.time()
    due = await redis.zrangebyscore(SCHEDULED_KEY, "-inf", now)
    for raw_id in due:
        async with redis.pipeline(transaction=True) as pipe:
            await pipe.zrem(SCHEDULED_KEY, raw_id)
            await pipe.rpush(READY_KEY, raw_id)
            await pipe.execute()


async def requeue_pending() -> None:
    """Recuperación tras un reinicio: cualquier entrega que haya quedado en
    'pending' (ni entregada ni agotada) se vuelve a encolar. Se pierde el
    backoff exacto que llevaba, pero no la entrega en sí."""
    async with db_session.async_session_factory() as db:
        result = await db.execute(
            select(WebhookDelivery.id).where(WebhookDelivery.status == "pending")
        )
        ids = result.scalars().all()
    for delivery_id in ids:
        await enqueue(delivery_id)
    if ids:
        logger.info("webhook_deliveries_requeued", count=len(ids))


async def _process_one(delivery_id: UUID) -> None:
    async with db_session.async_session_factory() as db:
        delivery = await db.get(WebhookDelivery, delivery_id)
        if delivery is None or delivery.status != "pending":
            return
        endpoint = await db.get(WebhookEndpoint, delivery.webhook_endpoint_id)
        if endpoint is None or not endpoint.is_active:
            delivery.status = "dead_letter"
            delivery.last_error = "Endpoint no encontrado o inactivo"
            await db.commit()
            return

        body = json.dumps(
            {
                "event_id": str(delivery.event_id),
                "event": delivery.event_type,
                "data": delivery.payload,
            }
        ).encode()
        timestamp = str(int(time.time()))
        signature = webhooks.sign_payload(endpoint.secret, timestamp, body)
        headers = {
            "Content-Type": "application/json",
            "X-Signature": signature,
            "X-Timestamp": timestamp,
        }

        delivery.attempt_count += 1
        attempt_index = delivery.attempt_count - 1
        try:
            status_code = await webhooks._send(endpoint.url, body, headers)
            delivery.last_status_code = status_code
            if 200 <= status_code < 300:
                delivery.status = "success"
                await db.commit()
                return
            delivery.last_error = f"HTTP {status_code}"
        except Exception as exc:
            delivery.last_error = str(exc)[:500]
            logger.warning(
                "webhook_delivery_attempt_failed",
                webhook_endpoint_id=str(endpoint.id),
                attempt=delivery.attempt_count,
                error=str(exc),
            )

        if delivery.attempt_count >= MAX_ATTEMPTS:
            delivery.status = "dead_letter"
            await db.commit()
        else:
            await db.commit()
            await _schedule_retry(delivery_id, BACKOFF_SECONDS[attempt_index])


async def run_worker(stop_event: asyncio.Event | None = None) -> None:
    """Loop del worker: promueve reintentos vencidos del ZSET de Redis a la
    lista de listos, y consume esa lista con BLPOP. Corre como una tarea de
    asyncio de larga duración (una por proceso backend), no por request."""
    redis = get_redis()
    while stop_event is None or not stop_event.is_set():
        await _promote_due_retries()
        popped = await redis.blpop([READY_KEY], timeout=POLL_TIMEOUT_SECONDS)
        if popped is None:
            continue
        _, raw_id = popped
        try:
            await _process_one(UUID(raw_id))
        except Exception:
            logger.exception("webhook_delivery_worker_error", delivery_id=raw_id)
