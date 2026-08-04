from pydantic import BaseModel

from app.schemas.common import ReadBase


class FAQCreate(BaseModel):
    question: str
    answer: str
    category: str | None = None


class FAQUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    category: str | None = None


class FAQRead(ReadBase):
    question: str
    answer: str
    category: str | None
