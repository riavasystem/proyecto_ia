from datetime import date

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Promotion(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "promotions"

    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    conditions: Mapped[str | None] = mapped_column(nullable=True)
    starts_on: Mapped[date | None] = mapped_column(nullable=True)
    ends_on: Mapped[date | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
