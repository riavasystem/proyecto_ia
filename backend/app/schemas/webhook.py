from typing import Any
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.models.webhook import WEBHOOK_EVENTS
from app.schemas.common import ReadBase


class WebhookEndpointCreate(BaseModel):
    url: str
    events: list[str]

    @field_validator("events")
    @classmethod
    def validate_events(cls, value: list[str]) -> list[str]:
        invalid = sorted(set(value) - set(WEBHOOK_EVENTS))
        if invalid:
            raise ValueError(f"Eventos inválidos: {', '.join(invalid)}")
        return value


class WebhookEndpointUpdate(BaseModel):
    url: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None

    @field_validator("events")
    @classmethod
    def validate_events(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        invalid = sorted(set(value) - set(WEBHOOK_EVENTS))
        if invalid:
            raise ValueError(f"Eventos inválidos: {', '.join(invalid)}")
        return value


class WebhookEndpointRead(ReadBase):
    url: str
    events: list[str]
    is_active: bool


class WebhookEndpointCreated(WebhookEndpointRead):
    secret: str
    """Valor en texto plano. Se muestra completo solo en esta respuesta."""


class WebhookDeliveryRead(ReadBase):
    webhook_endpoint_id: UUID
    event_type: str
    event_id: UUID
    payload: dict[str, Any]
    status: str
    attempt_count: int
    last_status_code: int | None
    last_error: str | None
