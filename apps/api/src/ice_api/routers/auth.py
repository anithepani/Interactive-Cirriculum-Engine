from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from jose import jwt as jose_jwt
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ice_shared import settings
from ice_shared.db import get_session
from ice_api.auth_utils import (
    create_access_token,
    create_refresh_token,
    generate_verification_code,
    get_current_user,
    hash_password,
    is_valid_email,
    sanitize_input,
    verify_password,
)
from ice_api.email_service import send_verification_email
from ice_api.models import Tenant, User, VerificationCode

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


# --- Pydantic models ---


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


# --- Helpers ---


async def create_user_and_tenant(
    session: AsyncSession,
    email: str,
    name: str,
    hashed_password: str | None = None,
    oauth_provider: str | None = None,
    oauth_id: str | None = None,
    is_verified: bool = False,
) -> User:
    tenant = Tenant(
        name=f"{name}'s Workspace",
        slug=f"{sanitize_input(name.lower())}-{secrets.token_hex(4)}",
    )
    session.add(tenant)
    await session.flush()

    user = User(
        tenant_id=tenant.id,
        email=email,
        name=sanitize_input(name),
        password_hash=hashed_password,
        oauth_provider=oauth_provider,
        oauth_id=oauth_id,
        is_verified=is_verified,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def verify_code(session: AsyncSession, email: str, code: str) -> bool:
    stmt = select(VerificationCode).where(
        and_(
            VerificationCode.email == email,
            VerificationCode.code == code,
            VerificationCode.is_used == False,
            VerificationCode.expires_at > datetime.utcnow(),
        )
    )
    result = await session.execute(stmt)
    vc = result.scalar_one_or_none()
    if vc:
        vc.is_used = True
        await session.commit()
        return True
    return False


def _token_redirect(access_token: str, refresh_token: str) -> RedirectResponse:
    """Redirect to frontend callback with tokens in query params."""
    params = urlencode({"access_token": access_token, "refresh_token": refresh_token})
    return RedirectResponse(f"{settings.frontend_url}/auth/callback?{params}")


def _user_dict(user: User) -> dict:
    return {
        "id": user.id, 
        "name": user.name, 
        "email": user.email,
        "avatar_url": user.avatar_url,
        "streak_count": user.streak_count,
        "streak_color": user.streak_color
    }


# --- OAuth ---


@router.get("/google/authorize")
async def google_authorize():
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/google/callback")
async def google_callback(code: str, session: AsyncSession = Depends(get_session)):
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_data = token_resp.json()
        if "id_token" not in token_data:
            raise HTTPException(status_code=400, detail="Failed to get ID token")

        user_info = jose_jwt.get_unverified_claims(token_data["id_token"])
        email = user_info.get("email")
        email_verified = user_info.get("email_verified", False)
        name = user_info.get("name", email.split("@")[0] if email else "User")
        google_id = user_info.get("sub")

        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
        if not email_verified:
            raise HTTPException(status_code=403, detail="Unverified Google emails are not permitted")

        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = await create_user_and_tenant(
                session,
                email,
                name,
                oauth_provider="google",
                oauth_id=google_id,
                is_verified=True,
            )
            await session.commit()
        else:
            if not user.oauth_id:
                user.oauth_provider = "google"
                user.oauth_id = google_id
            user.last_login = datetime.utcnow()
            await session.commit()

        access_token = create_access_token({"sub": str(user.id), "tv": user.token_version})
        refresh_token = create_refresh_token({"sub": str(user.id), "tv": user.token_version})
        return _token_redirect(access_token, refresh_token)


@router.get("/github/authorize")
async def github_authorize():
    params = {
        "client_id": settings.github_oauth_client_id,
        "redirect_uri": settings.github_oauth_redirect_uri,
        "scope": "user:email",
    }
    url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url)


@router.get("/github/callback")
async def github_callback(code: str, session: AsyncSession = Depends(get_session)):
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_oauth_client_id,
                "client_secret": settings.github_oauth_client_secret,
                "code": code,
                "redirect_uri": settings.github_oauth_redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        gh_token = token_data.get("access_token")
        if not gh_token:
            raise HTTPException(status_code=400, detail="Failed to get access token")

        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {gh_token}"},
        )
        user_data = user_resp.json()

        email_resp = await client.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {gh_token}"},
        )
        emails = email_resp.json()
        primary_email = next((e for e in emails if e.get("primary")), None)
        email = primary_email.get("email") if primary_email else user_data.get("email")
        is_verified = primary_email.get("verified") if primary_email else False

        if not email:
            raise HTTPException(status_code=400, detail="Email not found")
        if not is_verified:
            raise HTTPException(status_code=403, detail="Unverified GitHub emails are not permitted")

        name = user_data.get("name") or user_data.get("login") or email.split("@")[0]
        github_id = str(user_data.get("id"))

        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = await create_user_and_tenant(
                session,
                email,
                name,
                oauth_provider="github",
                oauth_id=github_id,
                is_verified=True,
            )
            await session.commit()
        else:
            if not user.oauth_id:
                user.oauth_provider = "github"
                user.oauth_id = github_id
            user.last_login = datetime.utcnow()
            await session.commit()

        access_token = create_access_token({"sub": str(user.id), "tv": user.token_version})
        refresh_token = create_refresh_token({"sub": str(user.id), "tv": user.token_version})
        return _token_redirect(access_token, refresh_token)


# --- Email/password auth ---


@router.post("/signup", response_model=dict)
async def signup(data: SignupRequest, session: AsyncSession = Depends(get_session)):
    if not is_valid_email(data.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    name = sanitize_input(data.name)
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters")

    stmt = select(User).where(User.email == data.email)
    result = await session.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(data.password)
    await create_user_and_tenant(
        session, data.email, name, hashed_password=hashed, is_verified=False
    )

    code = generate_verification_code()
    vc = VerificationCode(
        email=data.email,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    session.add(vc)
    await session.commit()

    await send_verification_email(data.email, code, name)
    return {"message": "Verification code sent to your email", "email": data.email}


@router.post("/verify", response_model=TokenResponse)
async def verify_account(
    data: VerifyCodeRequest, session: AsyncSession = Depends(get_session)
):
    if not is_valid_email(data.email):
        raise HTTPException(status_code=400, detail="Invalid email")

    if not await verify_code(session, data.email, data.code):
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    stmt = select(User).where(User.email == data.email)
    result = await session.execute(stmt)
    user = result.scalar_one()

    user.is_verified = True
    user.last_login = datetime.utcnow()
    await session.commit()

    access_token = create_access_token({"sub": str(user.id), "tv": user.token_version})
    refresh_token = create_refresh_token({"sub": str(user.id), "tv": user.token_version})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_user_dict(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, session: AsyncSession = Depends(get_session)):
    if not is_valid_email(data.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    stmt = select(User).where(User.email == data.email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    user.last_login = datetime.utcnow()
    await session.commit()

    access_token = create_access_token({"sub": str(user.id), "tv": user.token_version})
    refresh_token = create_refresh_token({"sub": str(user.id), "tv": user.token_version})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_user_dict(user),
    )


@router.post("/resend-code")
async def resend_code(email: str, session: AsyncSession = Depends(get_session)):
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Invalid email")

    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    # Invalidate previous codes
    stmt_invalidate = select(VerificationCode).where(
        and_(
            VerificationCode.email == email,
            VerificationCode.is_used == False
        )
    )
    res_inv = await session.execute(stmt_invalidate)
    for old_code in res_inv.scalars():
        old_code.is_used = True
    await session.commit()

    code = generate_verification_code()
    vc = VerificationCode(
        email=email,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    session.add(vc)
    await session.commit()

    await send_verification_email(email, code, user.name)
    return {"message": "Verification code resent"}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return _user_dict(current_user)


@router.post("/refresh")
async def refresh_token(
    data: RefreshRequest, session: AsyncSession = Depends(get_session)
):
    try:
        payload = jose_jwt.decode(
            data.refresh_token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        token_version = payload.get("tv", 1)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    stmt = select(User).where(User.id == int(user_id), User.is_active == True)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user or user.token_version != token_version:
        raise HTTPException(status_code=401, detail="User not found or session revoked")

    access_token = create_access_token({"sub": str(user.id), "tv": user.token_version})
    return {"access_token": access_token}

class UpdateMeRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    current_password: str | None = None
    new_password: str | None = Field(None, min_length=8)
    avatar_url: str | None = None
    streak_color: str | None = None

@router.put("/me")
async def update_me(
    data: UpdateMeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if data.new_password:
        if not data.current_password:
            raise HTTPException(status_code=400, detail="Current password is required to set a new password")
        if not current_user.password_hash or not verify_password(data.current_password, current_user.password_hash):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
            
        current_user.password_hash = hash_password(data.new_password)
        current_user.token_version += 1
        
    current_user.name = sanitize_input(data.name)
    
    if data.avatar_url is not None:
        current_user.avatar_url = data.avatar_url
    if data.streak_color is not None:
        current_user.streak_color = data.streak_color
    
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    
    return _user_dict(current_user)

