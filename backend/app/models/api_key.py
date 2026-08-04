from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

# Scopes soportados (sección 10.2 del CLAUDE.md).
API_KEY_SCOPES = (
    "chat:write",
    "conversations:read",
    "catalog:read",
    "catalog:write",
    "plugins:execute",
    "webhooks:manage",
)


class ApiKey(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "api_keys"

    name: Mapped[str] = mapped_column(nullable=False)
    key_prefix: Mapped[str] = mapped_column(nullable=False)
    key_hash: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    environment: Mapped[str] = mapped_column(nullable=False)  # "live" | "test"
    scopes: Mapped[str] = mapped_column(nullable=False, default="")
    """Lista separada por comas, ver API_KEY_SCOPES."""
    rate_limit_per_minute: Mapped[int] = mapped_column(default=60)
    is_active: Mapped[bool] = mapped_column(default=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)

    @property
    def scopes_list(self) -> list[str]:
        return [s for s in self.scopes.split(",") if s]
