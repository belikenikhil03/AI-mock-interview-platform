"""
Main FastAPI application.
Run from backend/: uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base

from app.models.user import User                  # noqa
from app.models.resume import Resume              # noqa
from app.models.interview import Interview        # noqa
from app.models.feedback import Feedback          # noqa
from app.models.metric import InterviewMetric     # noqa

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered mock interview platform",
    debug=settings.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Next.js frontend
        "http://localhost:3001",
        "http://localhost:8080",   # HTML tester (python -m http.server)
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5500",   # VS Code Live Server
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.endpoints.auth_endpoints      import router as auth_router
from app.api.endpoints.resume_endpoints    import router as resumes_router
from app.api.endpoints.interview_endpoints import router as interviews_router
from app.api.endpoints.feedback_endpoints   import router as feedback_router

app.include_router(auth_router,       prefix="/api/auth",       tags=["Authentication"])
app.include_router(resumes_router,    prefix="/api/resumes",    tags=["Resumes"])
app.include_router(interviews_router, prefix="/api/interviews", tags=["Interviews"])
app.include_router(feedback_router,   prefix="/api/feedback",   tags=["Feedback"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "AI Mock Interview Platform API",
        "version": settings.APP_VERSION,
        "status":  "operational"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "environment": settings.ENVIRONMENT}