from uuid import UUID

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token

PUBLIC_PATH_PREFIXES = ("/api/v1/public/health", "/docs", "/openapi.json", "/api/v1/openapi.json")


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Resuelve company_id desde el JWT o la API key y lo deja en request.state.

    El company_id NUNCA se acepta desde el body o query params del cliente.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.company_id = None
        request.state.user_id = None

        if request.url.path.startswith(PUBLIC_PATH_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ")
            try:
                payload = decode_token(token)
                request.state.company_id = UUID(payload["company_id"])
                request.state.user_id = UUID(payload["sub"])
            except Exception as exc:
                raise UnauthorizedError("Token inválido o expirado") from exc

        return await call_next(request)
