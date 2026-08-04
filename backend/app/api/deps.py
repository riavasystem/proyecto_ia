from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request

from app.core.exceptions import UnauthorizedError


def get_current_company_id(request: Request) -> UUID:
    company_id: UUID | None = getattr(request.state, "company_id", None)
    if company_id is None:
        raise UnauthorizedError("Autenticación requerida")
    return company_id


def get_current_user_id(request: Request) -> UUID:
    user_id: UUID | None = getattr(request.state, "user_id", None)
    if user_id is None:
        raise UnauthorizedError("Autenticación requerida")
    return user_id


CurrentCompanyId = Annotated[UUID, Depends(get_current_company_id)]
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
