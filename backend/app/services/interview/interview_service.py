"""
Interview service - manages interview session lifecycle.
Create → Start → Track → End → Save
"""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.interview import Interview, InterviewStatus
from app.models.resume import Resume
from app.models.user import User
from app.core.config import settings


class InterviewService:

    def create_session(
        self,
        db: Session,
        user: User,
        resume_id: int = None,
        interview_type: str = "job_role"
    ) -> Interview:
        """
        Create a new interview session.
        Validates rate limit, pulls job_role from resume if provided.
        """
        # ── Rate limit check ──────────────────────────────────────────────────
        from sqlalchemy import func, cast, Date
        today_count = (
            db.query(Interview)
            .filter(
                Interview.user_id == user.id,
                Interview.status != InterviewStatus.CANCELLED,
                func.cast(Interview.created_at, Date) == datetime.utcnow().date()
            )
            .count()
        )
        if today_count >= settings.MAX_INTERVIEWS_PER_DAY:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily limit of {settings.MAX_INTERVIEWS_PER_DAY} interviews reached. Try again tomorrow."
            )

        # ── Get job role from resume ──────────────────────────────────────────
        job_role = None
        if resume_id:
            resume = (
                db.query(Resume)
                .filter(Resume.id == resume_id, Resume.user_id == user.id)
                .first()
            )
            if not resume:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Resume not found"
                )
            job_role = resume.job_role

        # ── Create session ────────────────────────────────────────────────────
        interview = Interview(
            user_id        = user.id,
            resume_id      = resume_id,
            session_id     = str(uuid.uuid4()),
            status         = InterviewStatus.PENDING,
            job_role       = job_role,
            interview_type = interview_type
        )

        db.add(interview)
        db.commit()
        db.refresh(interview)
        return interview

    def start_session(self, db: Session, session_id: str, user_id: int) -> Interview:
        """Mark interview as in progress."""
        interview = self._get_session(db, session_id, user_id)

        if interview.status != InterviewStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Interview is already {interview.status}"
            )

        interview.status     = InterviewStatus.IN_PROGRESS
        interview.started_at = datetime.utcnow()
        db.commit()
        db.refresh(interview)
        return interview

    def end_session(
        self,
        db: Session,
        session_id: str,
        user_id: int,
        questions_asked: list = None,
        responses_given: list = None,
        video_blob_url: str = None
    ) -> Interview:
        """Mark interview as completed and save conversation data."""
        interview = self._get_session(db, session_id, user_id)

        if interview.status == InterviewStatus.COMPLETED:
            return interview  # already ended

        # Calculate duration
        duration = None
        if interview.started_at:
            delta = datetime.utcnow() - interview.started_at.replace(tzinfo=None)
            duration = int(delta.total_seconds())

        interview.status          = InterviewStatus.COMPLETED
        interview.completed_at    = datetime.utcnow()
        interview.duration_seconds = duration
        interview.questions_asked = questions_asked or []
        interview.responses_given = responses_given or []

        if video_blob_url:
            interview.video_blob_url = video_blob_url

        db.commit()
        db.refresh(interview)
        return interview

    def cancel_session(self, db: Session, session_id: str, user_id: int) -> Interview:
        """Cancel a pending or in-progress interview."""
        interview = self._get_session(db, session_id, user_id)
        interview.status = InterviewStatus.CANCELLED
        db.commit()
        db.refresh(interview)
        return interview

    def get_user_interviews(self, db: Session, user_id: int) -> list:
        """Get all interviews for a user, newest first."""
        return (
            db.query(Interview)
            .filter(Interview.user_id == user_id)
            .order_by(Interview.created_at.desc())
            .all()
        )

    def _get_session(self, db: Session, session_id: str, user_id: int) -> Interview:
        """Fetch interview and verify ownership."""
        interview = (
            db.query(Interview)
            .filter(
                Interview.session_id == session_id,
                Interview.user_id    == user_id
            )
            .first()
        )
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview session not found"
            )
        return interview
