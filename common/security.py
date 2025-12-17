"""
安全认证模块
提供密码哈希和 JWT 令牌相关功能

注意：直接使用 bcrypt 后端，避免 passlib+bcrypt 在 Windows/Python 3.13 上的兼容性问题
"""
from datetime import datetime, timedelta
import uuid
import bcrypt
from jose import jwt, JWTError


def hash_password(raw: str) -> str:
    """对密码进行哈希加密"""
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(raw: str, hashed: str) -> bool:
    """验证密码是否正确"""
    return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))


def create_token(data: dict, expires_delta: timedelta, secret: str, alg: str) -> str:
    """创建 JWT 令牌"""
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + expires_delta, "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, secret, algorithm=alg)


def decode_token(token: str, secret: str, alg: str) -> dict:
    """解码 JWT 令牌"""
    return jwt.decode(token, secret, algorithms=[alg])
