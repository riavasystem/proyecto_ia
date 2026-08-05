import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

# Eventos salientes soportados (sección 10.6 del CLAUDE.md). Los plugins
# pueden declarar eventos propios en su manifiesto — esos no están acá
# porque el Core no los conoce de antemano.
WEBHOOK_EVENTS = (
    "message.received",
    "message.replied",
    "conversation.started",
    "conversation.closed",
    "handoff.requested",
    "plugin.executed",
)


class WebhookEndpoint(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "webhook_endpoints"

    url: Mapped[str] = mapped_column(nullable=False)
    events: Mapped[str] = mapped_column(nullable=False, default="")
    """Lista separada por comas, ver WEBHOOK_EVENTS."""
    secret: Mapped[str] = mapped_column(nullable=False)
    """En texto plano: a diferencia de una API key, hay que poder reproducirlo
    para firmar cada entrega (HMAC), no solo verificarlo contra un candidato.
    Cifrarlo en reposo queda pendiente (mismo nivel de madurez que el resto
    del manejo de secretos del proyecto por ahora)."""
    is_active: Mapped[bool] = mapped_column(default=True)

    @property
    def events_list(self) -> list[str]:
        return [e for e in self.events.split(",") if e]


class WebhookDelivery(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "webhook_deliveries"

    webhook_endpoint_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("webhook_endpoints.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, unique=True)
    """Único por entrega, para que el receptor pueda deduplicar (sección 10.6)."""
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    """pending | success | dead_letter"""
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
