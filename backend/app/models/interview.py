"""
Updated Interview model with video recording support.
REPLACE: backend/app/models/interview.py
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base


class InterviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    
    status = Column(Enum(InterviewStatus), default=InterviewStatus.PENDING)
    job_role = Column(String(255), nullable=True)
    interview_type = Column(String(100), default="job_role")
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Interview data
    questions_asked = Column(JSON, nullable=True)
    responses_given = Column(JSON, nullable=True)
    
    # Video recording - NEW
    video_blob_url = Column(String(500), nullable=True)
    video_duration_seconds = Column(Integer, nullable=True)
    total_events_count = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="interviews")
    resume = relationship("Resume", back_populates="interviews")
    feedback = relationship("Feedback", back_populates="interview", uselist=False)
    metrics = relationship("InterviewMetric", back_populates="interview")
    events = relationship("InterviewEvent", back_populates="interview", cascade="all, delete-orphan")