import asyncio
import hashlib
import hmac
import json
import time
import uuid
from typing import Any
from uuid import UUID

import httpx
from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.session as db_session
from app.core.logging import get_logger
from app.models.webhook import WebhookDelivery, WebhookEndpoint

logger = get_logger(service="webhooks")

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (2.0, 10.0, 30.0)
DELIVERY_TIMEOUT_SECONDS = 5.0


def sign_payload(secret: str, timestamp: str, body: bytes) -> str:
    """HMAC-SHA256 sobre "{timestamp}.{body}", para que el receptor pueda
    rechazar entregas viejas reenviadas (protección contra replay, sección
    10.6 del CLAUDE.md)."""
    message = timestamp.encode() + b"." + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


async def emit_event(
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    company_id: UUID,
    event_type: str,
    data: dict[str, Any],
) -> None:
    """Crea una WebhookDelivery por cada endpoint del tenant suscripto a
    event_type, y programa su envío para después de que la respuesta HTTP ya
    se mandó (BackgroundTasks). MVP en proceso, no una cola persistente en
    Redis: si el proceso se reinicia a mitad de un reintento, ese reintento
    se pierde — queda documentado como pendiente en avances.md."""
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.company_id == company_id, WebhookEndpoint.is_active.is_(True)
        )
    )
    endpoints = [e for e in result.scalars().all() if event_type in e.events_list]
    if not endpoints:
        return

    delivery_ids: list[UUID] = []
    for endpoint in endpoints:
        delivery = WebhookDelivery(
            company_id=company_id,
            webhook_endpoint_id=endpoint.id,
            event_type=event_type,
            event_id=uuid.uuid4(),
            payload=data,
            status="pending",
        )
        db.add(delivery)
        await db.flush()
        delivery_ids.append(delivery.id)
    await db.commit()

    for delivery_id in delivery_ids:
        background_tasks.add_task(_deliver_with_retries, delivery_id)


async def _deliver_with_retries(delivery_id: UUID) -> None:
    async with db_session.async_session_factory() as db:
        delivery = await db.get(WebhookDelivery, delivery_id)
        if delivery is None:
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
        signature = sign_payload(endpoint.secret, timestamp, body)
        headers = {
            "Content-Type": "application/json",
            "X-Signature": signature,
            "X-Timestamp": timestamp,
        }

        for attempt in range(MAX_ATTEMPTS):
            delivery.attempt_count += 1
            try:
                status_code = await _send(endpoint.url, body, headers)
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
                    attempt=attempt + 1,
                    error=str(exc),
                )
            await db.commit()
            if attempt < MAX_ATTEMPTS - 1:
                await asyncio.sleep(BACKOFF_SECONDS[attempt])

        delivery.status = "dead_letter"
        await db.commit()


async def _send(url: str, body: bytes, headers: dict[str, str]) -> int:
    """Aislado en su propia función para poder monkeypatchearlo en tests sin
    depender de red real."""
    async with httpx.AsyncClient(timeout=DELIVERY_TIMEOUT_SECONDS) as client:
        response = await client.post(url, content=body, headers=headers)
        return response.status_code
