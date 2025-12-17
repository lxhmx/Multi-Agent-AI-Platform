"""
会话相关的 Pydantic 模型
"""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel


class SessionCreate(BaseModel):
    """创建会话请求"""
    title: Optional[str] = None


class SessionUpdate(BaseModel):
    """更新会话请求"""
    title: str


class MessageCreate(BaseModel):
    """创建消息请求"""
    role: Literal['user', 'assistant']
    content: str


class MessageResponse(BaseModel):
    """消息响应"""
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    """会话响应"""
    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int

    class Config:
        from_attributes = True


class SessionDetailResponse(SessionResponse):
    """会话详情响应（包含消息列表）"""
    messages: List[MessageResponse]


class SessionListResponse(BaseModel):
    """会话列表响应"""
    sessions: List[SessionResponse]
    total: int
    page: int
    page_size: int
