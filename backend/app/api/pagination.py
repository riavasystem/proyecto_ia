import base64
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, tuple_

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class CursorPage[T](BaseModel):
    data: list[T]
    next_cursor: str | None = None


class CursorParams(BaseModel):
    cursor: str | None = None
    limit: int = DEFAULT_LIMIT


def cursor_params(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
) -> CursorParams:
    return CursorParams(cursor=cursor, limit=limit)


def encode_cursor(created_at: datetime, item_id: UUID) -> str:
    raw = f"{created_at.isoformat()}|{item_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    created_at_raw, id_raw = raw.rsplit("|", 1)
    return datetime.fromisoformat(created_at_raw), UUID(id_raw)


def apply_cursor(query: Select, model: type[Any], params: CursorParams) -> Select:  # type: ignore[type-arg]
    """Pagina por (created_at, id) — orden estable incluso con timestamps
    empatados. Se pide limit+1 para saber si hay una página siguiente sin una
    segunda query (sección 10.7 del CLAUDE.md: paginación por cursor)."""
    query = query.order_by(model.created_at, model.id)
    if params.cursor:
        created_at, item_id = decode_cursor(params.cursor)
        query = query.where(tuple_(model.created_at, model.id) > (created_at, item_id))
    return query.limit(params.limit + 1)


def build_page(items: list[Any], params: CursorParams) -> tuple[list[Any], str | None]:
    has_more = len(items) > params.limit
    page_items = items[: params.limit]
    next_cursor = (
        encode_cursor(page_items[-1].created_at, page_items[-1].id)
        if has_more and page_items
        else None
    )
    return page_items, next_cursor
