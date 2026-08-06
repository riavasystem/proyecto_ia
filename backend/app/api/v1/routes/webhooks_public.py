import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentCompanyId, require_scope
from app.api.rate_limit import enforce_rate_limit
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.webhook import WebhookDelivery, WebhookEndpoint
from app.schemas.webhook import (
    WebhookDeliveryRead,
    WebhookEndpointCreate,
    WebhookEndpointCreated,
    WebhookEndpointRead,
    WebhookEndpointUpdate,
)

router = APIRouter(
    prefix="/webhooks",
    tags=["webhooks"],
    dependencies=[Depends(require_scope("webhooks:manage")), Depends(enforce_rate_limit)],
)

DbSession = Annotated[AsyncSession, Depends(get_db)]


def _to_read(endpoint: WebhookEndpoint) -> WebhookEndpointRead:
    return WebhookEndpointRead(
        id=endpoint.id,
        company_id=endpoint.company_id,
        created_at=endpoint.created_at,
        updated_at=endpoint.updated_at,
        url=endpoint.url,
        events=endpoint.events_list,
        is_active=endpoint.is_active,
    )


async def _get_owned_or_404(
    db: AsyncSession, company_id: UUID, webhook_id: UUID
) -> WebhookEndpoint:
    endpoint = await db.get(WebhookEndpoint, webhook_id)
    if endpoint is None or endpoint.company_id != company_id:
        raise NotFoundError("Webhook no encontrado")
    return endpoint


@router.post("", response_model=WebhookEndpointCreated, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    payload: WebhookEndpointCreate, company_id: CurrentCompanyId, db: DbSession
) -> WebhookEndpointCreated:
    secret = secrets.token_urlsafe(32)
    endpoint = WebhookEndpoint(
        company_id=company_id,
        url=payload.url,
        events=",".join(payload.events),
        secret=secret,
    )
    db.add(endpoint)
    await db.commit()
    await db.refresh(endpoint)
    return WebhookEndpointCreated(**_to_read(endpoint).model_dump(), secret=secret)


@router.get("", response_model=list[WebhookEndpointRead])
async def list_webhooks(company_id: CurrentCompanyId, db: DbSession) -> list[WebhookEndpointRead]:
    result = await db.execute(
        select(WebhookEndpoint)
        .where(WebhookEndpoint.company_id == company_id)
        .order_by(WebhookEndpoint.created_at)
    )
    return [_to_read(e) for e in result.scalars().all()]


@router.patch("/{webhook_id}", response_model=WebhookEndpointRead)
async def update_webhook(
    webhook_id: UUID, payload: WebhookEndpointUpdate, company_id: CurrentCompanyId, db: DbSession
) -> WebhookEndpointRead:
    endpoint = await _get_owned_or_404(db, company_id, webhook_id)
    updates = payload.model_dump(exclude_unset=True)
    if "events" in updates:
        endpoint.events = ",".join(updates.pop("events"))
    for field, value in updates.items():
        setattr(endpoint, field, value)
    await db.commit()
    await db.refresh(endpoint)
    return _to_read(endpoint)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(webhook_id: UUID, company_id: CurrentCompanyId, db: DbSession) -> None:
    endpoint = await _get_owned_or_404(db, company_id, webhook_id)
    await db.delete(endpoint)
    await db.commit()


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryRead])
async def list_deliveries(
    webhook_id: UUID, company_id: CurrentCompanyId, db: DbSession
) -> list[WebhookDeliveryRead]:
    await _get_owned_or_404(db, company_id, webhook_id)
    result = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_endpoint_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
    )
    return [WebhookDeliveryRead.model_validate(d) for d in result.scalars().all()]
