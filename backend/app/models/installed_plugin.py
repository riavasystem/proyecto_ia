from typing import Any

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class InstalledPlugin(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Estado de instalación de un plugin para un tenant. Es tabla del Core
    (administrar plugins es responsabilidad del Core, sección 4 del
    CLAUDE.md) — el plugin en sí vive fuera, en /plugins."""

    __tablename__ = "installed_plugins"

    plugin_name: Mapped[str] = mapped_column(nullable=False)
    version: Mapped[str] = mapped_column(nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_enabled: Mapped[bool] = mapped_column(default=True)
