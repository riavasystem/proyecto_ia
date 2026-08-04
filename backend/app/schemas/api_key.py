from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

from app.models.api_key import API_KEY_SCOPES
from app.schemas.common import ReadBase


class ApiKeyCreate(BaseModel):
    name: str
    environment: Literal["live", "test"] = "live"
    scopes: list[str]

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, value: list[str]) -> list[str]:
        invalid = sorted(set(value) - set(API_KEY_SCOPES))
        if invalid:
            raise ValueError(f"Scopes inválidos: {', '.join(invalid)}")
        return value


class ApiKeyRead(ReadBase):
    name: str
    key_prefix: str
    environment: str
    scopes: list[str]
    rate_limit_per_minute: int
    is_active: bool
    expires_at: datetime | None
    last_used_at: datetime | None


class ApiKeyCreated(ApiKeyRead):
    key: str
    """Valor en texto plano de la key. Solo se muestra en esta respuesta, una vez."""
