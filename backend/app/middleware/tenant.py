from uuid import UUID

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.exceptions import (
    DomainError,
    InvalidApiKeyError,
    UnauthorizedError,
    domain_error_handler,
)
from app.core.security import decode_token
from app.services.api_keys import resolve_api_key
from app.services.token_revocation import is_access_token_revoked

PUBLIC_PATH_PREFIXES = ("/api/v1/public/health", "/docs", "/openapi.json", "/api/v1/openapi.json")


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Resuelve company_id desde el JWT o la API key y lo deja en request.state.

    El company_id NUNCA se acepta desde el body o query params del cliente.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.company_id = None
        request.state.user_id = None
        request.state.api_key = None

        if request.url.path.startswith(PUBLIC_PATH_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ")
            # Se responde directamente con domain_error_handler (en vez de raise) porque
            # este middleware corre por fuera del ExceptionMiddleware de Starlette: una
            # excepción lanzada aquí no pasaría por los exception_handler registrados.
            error: DomainError
            if token.startswith("sk_"):
                api_key = await resolve_api_key(token)
                if api_key is None:
                    error = InvalidApiKeyError("API key inválida, revocada o expirada")
                    return await domain_error_handler(request, error)
                request.state.company_id = api_key.company_id
                request.state.api_key = api_key
            else:
                revoked = False
                try:
                    payload = decode_token(token)
                    company_id = UUID(payload["company_id"])
                    if payload.get("type") == "access":
                        revoked = await is_access_token_revoked(company_id, payload["jti"])
                except Exception:
                    error = UnauthorizedError("Token inválido o expirado")
                    return await domain_error_handler(request, error)
                if revoked:
                    error = UnauthorizedError("Token inválido o expirado")
                    return await domain_error_handler(request, error)
                request.state.company_id = company_id
                request.state.user_id = UUID(payload["sub"])

        return await call_next(request)
