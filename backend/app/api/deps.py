from collections.abc import Callable, Coroutine
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Request

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.models.api_key import ApiKey


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


def get_current_api_key(request: Request) -> ApiKey | None:
    key: ApiKey | None = getattr(request.state, "api_key", None)
    return key


CurrentApiKey = Annotated[ApiKey | None, Depends(get_current_api_key)]


def require_scope(scope: str) -> Callable[[Request], Coroutine[Any, Any, None]]:
    """Exige el scope solo cuando la request viene autenticada con API key.
    Las requests admin (JWT) no están limitadas por scopes de API key."""

    async def _check(request: Request) -> None:
        api_key: ApiKey | None = getattr(request.state, "api_key", None)
        if api_key is not None and scope not in api_key.scopes_list:
            raise ForbiddenError(f"La API key no tiene el scope requerido: {scope}")

    return _check
