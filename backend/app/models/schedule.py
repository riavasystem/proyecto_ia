import uuid
from datetime import date, time

from sqlalchemy import ForeignKey, Time, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class BusinessHour(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Horario semanal recurrente. day_of_week: 0=lunes ... 6=domingo."""

    __tablename__ = "business_hours"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False
    )
    day_of_week: Mapped[int] = mapped_column(nullable=False)
    opens_at: Mapped[time] = mapped_column(Time, nullable=False)
    closes_at: Mapped[time] = mapped_column(Time, nullable=False)


class ScheduleException(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Feriados o cambios puntuales de horario para una fecha específica."""

    __tablename__ = "schedule_exceptions"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False
    )
    exception_date: Mapped[date] = mapped_column(nullable=False)
    is_closed: Mapped[bool] = mapped_column(default=True)
    opens_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    closes_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    reason: Mapped[str | None] = mapped_column(nullable=True)
