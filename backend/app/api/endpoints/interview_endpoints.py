"""
Interview API endpoints.
Handles session creation, management, and WebSocket connection.
"""
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.api.dependencies.deps import get_current_user
from app.api.schemas.interview import (
    InterviewCreate,
    InterviewResponse,
    InterviewStartResponse,
    InterviewListResponse
)
from app.services.interview.interview_service import InterviewService
from app.websocket.voice_interview_handler import VoiceInterviewHandler as InterviewWebSocketHandler
from app.models.user import User
from app.core.security import decode_access_token
from app.core.database import SessionLocal
from app.models.user import User as UserModel

router = APIRouter()


@router.post(
    "/",
    response_model=InterviewStartResponse,
    status_code=201,
    summary="Create a new interview session"
)
async def create_interview(
    data: InterviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new interview session.
    Optionally link a resume for personalized questions.
    Returns a session_id and WebSocket URL to connect to.
    """
    service   = InterviewService()
    interview = service.create_session(
        db             = db,
        user           = current_user,
        resume_id      = data.resume_id,
        interview_type = data.interview_type
    )

    return {
        "session_id":    interview.session_id,
        "interview_id":  interview.id,
        "websocket_url": f"/api/interviews/{interview.session_id}/ws"
    }


@router.get(
    "/",
    response_model=List[InterviewResponse],
    summary="List all interviews for current user"
)
def list_interviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all interview sessions for the logged-in user."""
    service = InterviewService()
    return service.get_user_interviews(db, current_user.id)


@router.get(
    "/{session_id}",
    response_model=InterviewResponse,
    summary="Get a specific interview session"
)
def get_interview(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get details of a specific interview session."""
    service = InterviewService()
    return service._get_session(db, session_id, current_user.id)


@router.delete(
    "/{session_id}",
    status_code=204,
    summary="Cancel an interview session"
)
def cancel_interview(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a pending interview session."""
    service = InterviewService()
    service.cancel_session(db, session_id, current_user.id)


@router.websocket("/{session_id}/ws")
async def interview_websocket(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(..., description="JWT token for auth")
):
    """
    WebSocket endpoint for live interview session.

    Connect with: ws://localhost:8000/api/interviews/{session_id}/ws?token=<jwt>

    Message flow:
    1. Connect → server sends { type: "ready" }
    2. Server sends { type: "question", text: "..." }
    3. Client sends { type: "text", data: "my answer..." }
    4. Server sends { type: "metrics", ... }
    5. Repeat until all questions done or time limit
    6. Server sends { type: "ended", reason: "completed" }
    """
    # Authenticate via token query param (WebSocket can't use headers easily)
    db = SessionLocal()
    try:
        payload = decode_access_token(token)
        if not payload:
            await websocket.close(code=4001, reason="Invalid token")
            return

        user_id = int(payload.get("sub"))
        user    = db.query(UserModel).filter(UserModel.id == user_id).first()

        if not user or not user.is_active:
            await websocket.close(code=4001, reason="User not found")
            return

    finally:
        db.close()

    # Hand off to WebSocket handler
    handler = InterviewWebSocketHandler()
    await handler.handle(websocket, session_id, user_id)
