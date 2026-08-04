from fastapi import Request, status
from fastapi.responses import JSONResponse


class DomainError(Exception):
    code = "domain_error"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str, headers: dict[str, str] | None = None) -> None:
        self.message = message
        self.headers = headers or {}
        super().__init__(message)


class NotFoundError(DomainError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND


class UnauthorizedError(DomainError):
    code = "unauthorized"
    status_code = status.HTTP_401_UNAUTHORIZED


class InvalidApiKeyError(DomainError):
    code = "invalid_api_key"
    status_code = status.HTTP_401_UNAUTHORIZED


class ForbiddenError(DomainError):
    code = "forbidden"
    status_code = status.HTTP_403_FORBIDDEN


class RateLimitExceededError(DomainError):
    code = "rate_limit_exceeded"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id,
            }
        },
        headers=exc.headers,
    )
