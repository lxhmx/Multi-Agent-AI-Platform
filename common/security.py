"""
Security helpers for authentication: password hashing and JWT helpers.

Note: Use bcrypt backend directly to avoid passlib+bcrypt compatibility issues on Windows/Python 3.13.
"""
from datetime import datetime, timedelta
import uuid
import bcrypt
from jose import jwt, JWTError


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))


def create_token(data: dict, expires_delta: timedelta, secret: str, alg: str) -> str:
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + expires_delta, "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, secret, algorithm=alg)


def decode_token(token: str, secret: str, alg: str) -> dict:
    return jwt.decode(token, secret, algorithms=[alg])
