from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    external_user_id: str
    external_metadata: dict[str, Any] | None = None
    message: str


class ChatResponse(BaseModel):
    conversation_id: UUID
    reply: str
