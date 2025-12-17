"""
会话 API 模块
提供聊天会话和消息的增删改查接口
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

from schemas.session import (
    SessionCreate, SessionUpdate, SessionResponse, 
    SessionDetailResponse, SessionListResponse, MessageCreate, MessageResponse
)
from common.repositories import session_repo, message_repo
from common.dependencies import get_current_user

router = APIRouter(prefix="/api/sessions", tags=["会话管理"])


@router.get("", response_model=SessionListResponse)
async def get_sessions(
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """获取当前用户的会话列表（分页）"""
    sessions, total = session_repo.get_sessions_by_user(
        current_user["id"], page, page_size
    )
    return SessionListResponse(
        sessions=[SessionResponse(**s) for s in sessions],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建新的聊天会话"""
    session = session_repo.create_session(current_user["id"], data.title)
    return SessionResponse(**session)


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取会话详情（包含消息列表）"""
    session = session_repo.get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    if session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    
    messages = message_repo.get_messages_by_session(session_id)
    return SessionDetailResponse(
        **session,
        messages=[MessageResponse(**m) for m in messages]
    )


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    data: SessionUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新会话标题"""
    session = session_repo.get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    if session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    
    session_repo.update_session_title(session_id, data.title)
    updated_session = session_repo.get_session_by_id(session_id)
    return SessionResponse(**updated_session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """删除会话及其所有消息"""
    session = session_repo.get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    if session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    
    session_repo.delete_session(session_id)
    return None


@router.post("/{session_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message(
    session_id: str,
    data: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """向会话中添加消息"""
    session = session_repo.get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    if session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    
    # 如果会话没有标题，自动从第一条用户消息生成标题
    if not session["title"] and data.role == "user":
        title = data.content[:50] if len(data.content) > 50 else data.content
        session_repo.update_session_title(session_id, title)
    
    message = message_repo.create_message(session_id, data.role, data.content)
    return MessageResponse(**message)
