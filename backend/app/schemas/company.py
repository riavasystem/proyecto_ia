from pydantic import BaseModel

from app.schemas.common import TimestampedRead


class CompanyUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None


class CompanyRead(TimestampedRead):
    name: str
    industry: str | None
    email: str | None
    phone: str | None
    website: str | None
    is_active: bool
