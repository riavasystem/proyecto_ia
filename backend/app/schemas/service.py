from pydantic import BaseModel

from app.schemas.common import ReadBase


class ServiceCreate(BaseModel):
    name: str
    category: str | None = None
    description: str | None = None
    price: float | None = None
    estimated_minutes: int | None = None
    image_url: str | None = None
    is_active: bool = True


class ServiceUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    price: float | None = None
    estimated_minutes: int | None = None
    image_url: str | None = None
    is_active: bool | None = None


class ServiceRead(ReadBase):
    name: str
    category: str | None
    description: str | None
    price: float | None
    estimated_minutes: int | None
    image_url: str | None
    is_active: bool
