"""interview.py - Interview session model"""
import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class InterviewStatus(str, enum.Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    FAILED      = "failed"
    CANCELLED   = "cancelled"


class Interview(Base):
    __tablename__ = "interviews"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"),   nullable=False, index=True)
    resume_id      = Column(Integer, ForeignKey("resumes.id"), nullable=True,  index=True)
    session_id     = Column(String(100), unique=True, index=True, nullable=False)
    status         = Column(SQLEnum(InterviewStatus), default=InterviewStatus.PENDING, nullable=False)
    job_role       = Column(String(255), nullable=True)
    interview_type = Column(String(100), nullable=True)
    video_blob_url = Column(String(500), nullable=True)
    duration_seconds = Column(Integer,  nullable=True)
    questions_asked  = Column(JSON,     nullable=True)
    responses_given  = Column(JSON,     nullable=True)
    started_at     = Column(DateTime(timezone=True), nullable=True)
    completed_at   = Column(DateTime(timezone=True), nullable=True)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    user     = relationship("User",            back_populates="interviews")
    resume   = relationship("Resume",          back_populates="interviews")
    feedback = relationship("Feedback",        back_populates="interview", uselist=False, cascade="all, delete-orphan")
    metrics  = relationship("InterviewMetric", back_populates="interview", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Interview(id={self.id}, session_id='{self.session_id}', status='{self.status}')>"