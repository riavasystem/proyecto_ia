from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Product(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    sku: Mapped[str | None] = mapped_column(nullable=True)
    image_url: Mapped[str | None] = mapped_column(nullable=True)
    stock: Mapped[int | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
