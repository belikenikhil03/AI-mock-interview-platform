"""
Main FastAPI application - COMPLETE FILE
REPLACE: backend/app/main.py
"""
from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.security import decode_access_token

# Import all models so SQLAlchemy creates tables
from app.models.user import User as UserModel
from app.models.resume import Resume
from app.models.interview import Interview
from app.models.feedback import Feedback
from app.models.metric import InterviewMetric
from app.models.interview_event import InterviewEvent  # NEW

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered mock interview platform with voice",
    debug=settings.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
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
    db = SessionLocal()
    try:
        payload = decode_access_token(token)
        if not payload:
            await websocket.close(code=4001, reason="Invalid token")
            return

        user_id = int(payload.get("sub"))
        user = db.query(UserModel).filter(UserModel.id == user_id).first()

        if not user or not user.is_active:
            await websocket.close(code=4001, reason="User not found")
            return

    finally:
        db.close()

    # Use voice interview handler (NEW)
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