"""
COMPLETE top section of main.py - SQL logs WILL be fixed
REPLACE lines 1-30 of: backend/app/main.py
"""
import logging
import sys

# Configure logging FIRST - before ANY other imports
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    stream=sys.stdout
)

# Silence SQLAlchemy
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)

# NOW import everything
from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.security import decode_access_token

from app.models.user import User as UserModel
from app.models.resume import Resume
from app.models.interview import Interview
from app.models.feedback import Feedback
from app.models.metric import InterviewMetric
from app.models.interview_event import InterviewEvent

# Create tables
Base.metadata.create_all(bind=engine)

# Create app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered mock interview platform",
    debug=settings.DEBUG
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── All Routers ───────────────────────────────────────────────────────────────
from app.api.endpoints.auth_endpoints import router as auth_router
from app.api.endpoints.resume_endpoints import router as resumes_router
from app.api.endpoints.interview_endpoints import router as interviews_router
from app.api.endpoints.feedback_endpoints import router as feedback_router
from app.api.endpoints.recordings_endpoint import router as recordings_router
from app.api.endpoints.speech_endpoint import router as speech_router

app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(resumes_router, prefix="/api/resumes", tags=["Resumes"])
app.include_router(interviews_router, prefix="/api/interviews", tags=["Interviews"])
app.include_router(feedback_router, prefix="/api/feedback", tags=["Feedback"])
app.include_router(recordings_router, prefix="/api/recordings", tags=["Recordings"])
app.include_router(speech_router, prefix="/api/speech", tags=["Speech"])


# ── WebSocket for Voice Interview ────────────────────────────────────────────
from app.websocket.voice_interview_handler import VoiceInterviewHandler  # UPDATED

@app.websocket("/api/interviews/{session_id}/ws")
async def interview_websocket(
    websocket: WebSocket,
    session_id: str,
    token: str = Query(..., description="JWT token for auth")
):
    """
    WebSocket endpoint for VOICE-based interview session.
    """
    # Auth check (no database needed here)
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = int(payload.get("sub"))
    
    # Quick user validation
    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        print(f"@@@ USER FOUND: {user.email if user else 'NONE'} @@@")
        if not user or not user.is_active:
            await websocket.close(code=4001, reason="User not found")
            return
    finally:
        db.close()  # Close this temporary DB session

    # Now call handler - it will create its own DB session
    print("@@@ ABOUT TO CREATE VOICE HANDLER @@@")
    handler = VoiceInterviewHandler()
    await handler.handle(websocket, session_id, user_id)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "AI Mock Interview Platform API",
        "version": settings.APP_VERSION,
        "status": "operational"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "environment": settings.ENVIRONMENT}