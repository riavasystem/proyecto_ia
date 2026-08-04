from uuid import UUID

from app.schemas.common import ReadBase


class MessageRead(ReadBase):
    conversation_id: UUID
    role: str
    content: str
    intent: str | None


class ConversationRead(ReadBase):
    contact_id: UUID
    channel: str
    status: str


class ConversationDetailRead(ConversationRead):
    messages: list[MessageRead]
