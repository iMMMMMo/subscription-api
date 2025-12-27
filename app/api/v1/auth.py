from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_and_validate_token,
    get_current_subject,
)
from app.db.session import get_session
from app.schemas.token import RefreshTokenRequest, Token
from app.schemas.user import UserCreate, UserLogin, UserRead
from app.services.user_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
    get_user_by_id,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    session: AsyncSession = Depends(get_session),
):
    exitsting = await get_user_by_email(session, data.email)
    if exitsting:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = await create_user(
        session,
        email=data.email,
        password=data.password,
        full_name=data.full_name,
    )
    return user


@router.post("/login", response_model=Token)
async def login(
    data: UserLogin,
    session: AsyncSession = Depends(get_session),
):
    user = await authenticate_user(
        session,
        email=data.email,
        password=data.password,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh(data: RefreshTokenRequest):
    payload = decode_and_validate_token(
        token=data.refresh_token,
        expected_type="refresh",
    )
    subject = payload["sub"]
    access_token = create_access_token(subject)
    refresh_token = create_refresh_token(subject)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserRead)
async def me(
    subject: str = Depends(get_current_subject),
    session: AsyncSession = Depends(get_session),
):
    try:
        user_id = int(subject)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token subject",
        )

    user = await get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
