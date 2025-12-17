"""Pydantic schemas for chat session management."""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel


class SessionCreate(BaseModel):
    title: Optional[str] = None


class SessionUpdate(BaseModel):
    title: str


class MessageCreate(BaseModel):
    role: Literal['user', 'assistant']
    content: str


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    message_count: int

    class Config:
        from_attributes = True


class SessionDetailResponse(SessionResponse):
    messages: List[MessageResponse]


class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]
    total: int
    page: int
    page_size: int
