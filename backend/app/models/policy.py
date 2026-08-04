from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Policy(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    __tablename__ = "policies"

    type: Mapped[str] = mapped_column(nullable=False)
    """pagos | garantias | devoluciones | reservas | privacidad"""
    content: Mapped[str] = mapped_column(nullable=False)
