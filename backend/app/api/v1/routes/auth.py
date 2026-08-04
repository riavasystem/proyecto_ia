from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    existing = await db.execute(select(User).where(User.email == payload.admin_email))
    if existing.scalar_one_or_none() is not None:
        raise DomainError("Ya existe una cuenta con ese email")

    company = Company(name=payload.company_name)
    db.add(company)
    await db.flush()

    user = User(
        company_id=company.id,
        email=payload.admin_email,
        password_hash=hash_password(payload.admin_password),
        full_name=payload.admin_full_name,
        role="admin",
    )
    db.add(user)
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, company.id),
        refresh_token=create_refresh_token(user.id, company.id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    password_ok = user is not None and verify_password(payload.password, user.password_hash)
    if user is None or not user.is_active or not password_ok:
        raise UnauthorizedError("Credenciales inválidas")

    return TokenResponse(
        access_token=create_access_token(user.id, user.company_id),
        refresh_token=create_refresh_token(user.id, user.company_id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest) -> TokenResponse:
    try:
        decoded = decode_token(payload.refresh_token)
    except Exception as exc:
        raise UnauthorizedError("Refresh token inválido o expirado") from exc

    if decoded.get("type") != "refresh":
        raise UnauthorizedError("Token no es de tipo refresh")

    user_id = UUID(decoded["sub"])
    company_id = UUID(decoded["company_id"])

    return TokenResponse(
        access_token=create_access_token(user_id, company_id),
        refresh_token=create_refresh_token(user_id, company_id),
    )
