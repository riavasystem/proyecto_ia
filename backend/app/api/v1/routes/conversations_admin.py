from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentCompanyId
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.schemas.conversation import ConversationDetailRead, ConversationRead, MessageRead

router = APIRouter(prefix="/conversations", tags=["conversations"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=list[ConversationRead])
async def list_conversations(company_id: CurrentCompanyId, db: DbSession) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.company_id == company_id)
        .order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{conversation_id}", response_model=ConversationDetailRead)
async def get_conversation(
    conversation_id: UUID, company_id: CurrentCompanyId, db: DbSession
) -> ConversationDetailRead:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.company_id != company_id:
        raise NotFoundError("Conversación no encontrada")

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    messages = [MessageRead.model_validate(m) for m in result.scalars().all()]
    return ConversationDetailRead(
        **ConversationRead.model_validate(conversation).model_dump(), messages=messages
    )
