from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "users"

    # Único a nivel global (no por tenant): el login resuelve el company_id a partir
    # del email, antes de tener contexto de tenant.
    email: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    full_name: Mapped[str | None] = mapped_column(nullable=True)
    role: Mapped[str] = mapped_column(default="admin")
    is_active: Mapped[bool] = mapped_column(default=True)
