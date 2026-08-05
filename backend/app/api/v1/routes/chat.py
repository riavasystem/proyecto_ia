from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.engine import process_message
from app.api.deps import CurrentCompanyId, require_scope
from app.api.pagination import CursorPage, CursorParams, apply_cursor, build_page, cursor_params
from app.api.rate_limit import enforce_rate_limit
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.contact import Contact
from app.models.conversation import Conversation, Message
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.conversation import ConversationDetailRead, ConversationRead, MessageRead
from app.services.webhooks import emit_event

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
async def chat(
    payload: ChatRequest,
    company_id: CurrentCompanyId,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> ChatResponse:
    contact = await _get_or_create_contact(
        db, company_id, payload.external_user_id, payload.external_metadata
    )

    is_new_conversation = payload.conversation_id is None
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

    if is_new_conversation:
        await emit_event(
            db,
            background_tasks,
            company_id,
            "conversation.started",
            {"conversation_id": str(conversation.id), "external_user_id": payload.external_user_id},
        )
    await emit_event(
        db,
        background_tasks,
        company_id,
        "message.received",
        {"conversation_id": str(conversation.id), "message": payload.message},
    )
    await emit_event(
        db,
        background_tasks,
        company_id,
        "message.replied",
        {
            "conversation_id": str(conversation.id),
            "reply": reply.text,
            "intent": reply.intent.value,
        },
    )

    return ChatResponse(conversation_id=conversation.id, reply=reply.text)


@router.get(
    "/conversations",
    response_model=CursorPage[ConversationRead],
    dependencies=[Depends(require_scope("conversations:read")), Depends(enforce_rate_limit)],
)
async def list_conversations(
    company_id: CurrentCompanyId,
    db: DbSession,
    params: Annotated[CursorParams, Depends(cursor_params)],
    external_user_id: Annotated[str | None, Query()] = None,
) -> CursorPage[ConversationRead]:
    query = select(Conversation).where(Conversation.company_id == company_id)
    if external_user_id is not None:
        query = query.join(Contact, Contact.id == Conversation.contact_id).where(
            Contact.external_id == external_user_id
        )
    query = apply_cursor(query, Conversation, params)
    result = await db.execute(query)
    items, next_cursor = build_page(list(result.scalars().all()), params)
    return CursorPage(
        data=[ConversationRead.model_validate(c) for c in items], next_cursor=next_cursor
    )


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
    conversation_id: UUID,
    company_id: CurrentCompanyId,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> Conversation:
    conversation = await _get_conversation_or_404(db, company_id, conversation_id)
    conversation.status = "closed"
    await db.commit()
    await db.refresh(conversation)
    await emit_event(
        db,
        background_tasks,
        company_id,
        "conversation.closed",
        {"conversation_id": str(conversation.id)},
    )
    return conversation
