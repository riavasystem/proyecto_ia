from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TimestampedRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class ReadBase(TimestampedRead):
    """Para entidades de tenant (con company_id). Company usa TimestampedRead directo."""

    company_id: UUID
