from pydantic import BaseModel

from app.schemas.common import ReadBase


class ProductCreate(BaseModel):
    name: str
    description: str | None = None
    price: float | None = None
    sku: str | None = None
    image_url: str | None = None
    stock: int | None = None
    is_active: bool = True


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    sku: str | None = None
    image_url: str | None = None
    stock: int | None = None
    is_active: bool | None = None


class ProductRead(ReadBase):
    name: str
    description: str | None
    price: float | None
    sku: str | None
    image_url: str | None
    stock: int | None
    is_active: bool
