from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Contact(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Usuario final del proyecto externo que integra la plataforma (sección
    10.5 del CLAUDE.md). No es un User del panel: nunca se le pide que se
    registre acá, solo se referencia por el external_id que ya tiene en el
    sistema del tercero."""

    __tablename__ = "contacts"

    external_id: Mapped[str] = mapped_column(nullable=False)
    external_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
