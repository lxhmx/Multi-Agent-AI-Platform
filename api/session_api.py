"""Session API endpoints for chat history management."""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

from schemas.session import (
    SessionCreate, SessionUpdate, SessionResponse, 
    SessionDetailResponse, SessionListResponse, MessageCreate, MessageResponse
)
from common.repositories import session_repo, message_repo
from common.dependencies import get_current_user

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse)
async def get_sessions(
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get paginated session list for current user."""
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
    """Create a new chat session."""
    session = session_repo.create_session(current_user["id"], data.title)
    return SessionResponse(**session)


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get session detail with messages."""
    session = session_repo.get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
    
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
    """Update session title."""
    session = session_repo.get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
    
    session_repo.update_session_title(session_id, data.title)
    updated_session = session_repo.get_session_by_id(session_id)
    return SessionResponse(**updated_session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a session and all its messages."""
    session = session_repo.get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
    
    session_repo.delete_session(session_id)
    return None


@router.post("/{session_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message(
    session_id: str,
    data: MessageCreate,
    current_user: dict = Depends(get_current_user)
):
    """Add a message to a session."""
    session = session_repo.get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
    
    # Auto-generate title from first user message if no title set
    if not session["title"] and data.role == "user":
        title = data.content[:50] if len(data.content) > 50 else data.content
        session_repo.update_session_title(session_id, title)
    
    message = message_repo.create_message(session_id, data.role, data.content)
    return MessageResponse(**message)
