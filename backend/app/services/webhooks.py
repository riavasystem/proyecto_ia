import hashlib
import hmac
import uuid
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import WebhookDelivery, WebhookEndpoint

DELIVERY_TIMEOUT_SECONDS = 5.0


def sign_payload(secret: str, timestamp: str, body: bytes) -> str:
    """HMAC-SHA256 sobre "{timestamp}.{body}", para que el receptor pueda
    rechazar entregas viejas reenviadas (protección contra replay, sección
    10.6 del CLAUDE.md)."""
    message = timestamp.encode() + b"." + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


async def emit_event(
    db: AsyncSession,
    company_id: UUID,
    event_type: str,
    data: dict[str, Any],
) -> None:
    """Crea una WebhookDelivery por cada endpoint del tenant suscripto a
    event_type y la encola en Redis (webhook_queue) para que el worker de
    fondo la entregue. La entrega en sí no ocurre acá: esto solo persiste la
    intención de entregar, así que sobrevive a un reinicio del proceso."""
    # Import diferido: webhook_queue importa este módulo a nivel de archivo,
    # así que importarlo acá arriba crearía un ciclo en tiempo de carga.
    from app.services import webhook_queue

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
        await webhook_queue.enqueue(delivery_id)


async def _send(url: str, body: bytes, headers: dict[str, str]) -> int:
    """Aislado en su propia función para poder monkeypatchearlo en tests sin
    depender de red real."""
    async with httpx.AsyncClient(timeout=DELIVERY_TIMEOUT_SECONDS) as client:
        response = await client.post(url, content=body, headers=headers)
        return response.status_code
