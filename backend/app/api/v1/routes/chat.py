from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.engine import process_message
from app.api.deps import CurrentCompanyId, require_scope
from app.api.rate_limit import enforce_rate_limit
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.contact import Contact
from app.models.conversation import Conversation, Message
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.conversation import ConversationDetailRead, ConversationRead, MessageRead

router = APIRouter(tags=["chat"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def _get_or_create_contact(
    db: AsyncSession, company_id: UUID, external_id: str, external_metadata: dict[str, Any] | None
) -> Contact:
    result = await db.execute(
        select(Contact).where(Contact.company_id == company_id, Contact.external_id == external_id)
    )
    contact = result.scalar_one_or_none()
    if contact is None:
        contact = Contact(
            company_id=company_id, external_id=external_id, external_metadata=external_metadata
        )
        db.add(contact)
        await db.flush()
    elif external_metadata is not None:
        contact.external_metadata = external_metadata
    return contact


async def _get_conversation_or_404(
    db: AsyncSession, company_id: UUID, conversation_id: UUID
) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.company_id != company_id:
        raise NotFoundError("Conversación no encontrada")
    return conversation


@router.post(
    "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(require_scope("chat:write")), Depends(enforce_rate_limit)],
)
async def chat(payload: ChatRequest, company_id: CurrentCompanyId, db: DbSession) -> ChatResponse:
    contact = await _get_or_create_contact(
        db, company_id, payload.external_user_id, payload.external_metadata
    )

    if payload.conversation_id is not None:
        conversation = await _get_conversation_or_404(db, company_id, payload.conversation_id)
    else:
        conversation = Conversation(company_id=company_id, contact_id=contact.id)
        db.add(conversation)
        await db.flush()

    db.add(
        Message(
            company_id=company_id,
            conversation_id=conversation.id,
            role="user",
            content=payload.message,
        )
    )

    reply = await process_message(db, company_id, payload.message)

    db.add(
        Message(
            company_id=company_id,
            conversation_id=conversation.id,
            role="assistant",
            content=reply.text,
            intent=reply.intent.value,
        )
    )
    await db.commit()

    return ChatResponse(conversation_id=conversation.id, reply=reply.text)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailRead,
    dependencies=[Depends(require_scope("conversations:read")), Depends(enforce_rate_limit)],
)
async def get_conversation(
    conversation_id: UUID, company_id: CurrentCompanyId, db: DbSession
) -> ConversationDetailRead:
    conversation = await _get_conversation_or_404(db, company_id, conversation_id)
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    messages = [MessageRead.model_validate(m) for m in result.scalars().all()]
    return ConversationDetailRead(
        **ConversationRead.model_validate(conversation).model_dump(), messages=messages
    )


@router.post(
    "/conversations/{conversation_id}/close",
    response_model=ConversationRead,
    dependencies=[Depends(require_scope("chat:write")), Depends(enforce_rate_limit)],
)
async def close_conversation(
    conversation_id: UUID, company_id: CurrentCompanyId, db: DbSession
) -> Conversation:
    conversation = await _get_conversation_or_404(db, company_id, conversation_id)
    conversation.status = "closed"
    await db.commit()
    await db.refresh(conversation)
    return conversation
