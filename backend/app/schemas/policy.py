from typing import Literal

from pydantic import BaseModel

from app.schemas.common import ReadBase

PolicyType = Literal["pagos", "garantias", "devoluciones", "reservas", "privacidad"]


class PolicyCreate(BaseModel):
    type: PolicyType
    content: str


class PolicyUpdate(BaseModel):
    type: PolicyType | None = None
    content: str | None = None


class PolicyRead(ReadBase):
    type: str
    content: str
