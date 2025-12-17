"""
认证相关的 Pydantic 模型
"""
from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    """登录请求"""
    username: str
    password: str


class RefreshRequest(BaseModel):
    """刷新令牌请求"""
    refresh_token: str


class RegisterRequest(BaseModel):
    """注册请求"""
    username: str
    password: str
    email: Optional[EmailStr] = None


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserPublic(BaseModel):
    """用户公开信息"""
    id: int
    username: str
    email: Optional[EmailStr] = None
