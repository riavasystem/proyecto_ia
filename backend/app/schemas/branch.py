from pydantic import BaseModel

from app.schemas.common import ReadBase


class BranchCreate(BaseModel):
    name: str
    address: str | None = None
    phone: str | None = None
    is_active: bool = True


class BranchUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    is_active: bool | None = None


class BranchRead(ReadBase):
    name: str
    address: str | None
    phone: str | None
    is_active: bool
