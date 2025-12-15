"""
Authentication API: register, login, refresh, me.
"""
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Depends
from jose import JWTError

from common.security import hash_password, verify_password, create_token, decode_token
from common.repositories import user_repo
from schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)
from config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from common.dependencies import get_current_user


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserPublic)
def register(body: RegisterRequest):
    if user_repo.get_by_username(body.username):
        raise HTTPException(status_code=400, detail="Username exists")
    user_id = user_repo.create_user(body.username, body.email, hash_password(body.password))
    return UserPublic(id=user_id, username=body.username, email=body.email)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    user = user_repo.get_by_username(body.username)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access = create_token(
        {"sub": str(user["id"]), "type": "access"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        SECRET_KEY,
        ALGORITHM,
    )
    refresh = create_token(
        {"sub": str(user["id"]), "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        SECRET_KEY,
        ALGORITHM,
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token, SECRET_KEY, ALGORITHM)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Not a refresh token")
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access = create_token(
        {"sub": str(user_id), "type": "access"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        SECRET_KEY,
        ALGORITHM,
    )
    refresh_new = create_token(
        {"sub": str(user_id), "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        SECRET_KEY,
        ALGORITHM,
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh_new,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserPublic)
def me(user=Depends(get_current_user)):
    return UserPublic(id=user["id"], username=user["username"], email=user.get("email"))
