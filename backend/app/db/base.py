import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    """Timestamps generados en Python (no server_default) a propósito: el
    server_default de SQLite (CURRENT_TIMESTAMP) trunca a resolución de
    segundo y sin microsegundos, mientras que cualquier datetime Python
    vinculado luego para comparar (p. ej. paginación por cursor) sí lleva
    microsegundos — la comparación de texto en SQLite falla en silencio y
    excluye filas que deberían matchear. Generarlo en Python es consistente
    entre SQLite y Postgres y evita el problema de raíz."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class TenantMixin:
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
