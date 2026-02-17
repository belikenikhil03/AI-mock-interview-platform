"""metric.py - Interview real-time metrics model"""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class InterviewMetric(Base):
    __tablename__ = "interview_metrics"

    id           = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False, index=True)

    # Speech metrics
    filler_words_count     = Column(Integer, default=0)
    total_words_spoken     = Column(Integer, default=0)
    average_pause_duration = Column(Float,   default=0.0)
    longest_pause_duration = Column(Float,   default=0.0)
    speech_rate_wpm        = Column(Float,   default=0.0)

    # Video metrics (from MediaPipe)
    eye_contact_percentage = Column(Float,   default=0.0)
    fidgeting_count        = Column(Integer, default=0)
    posture_score          = Column(Float,   default=0.0)

    # Audio analysis
    voice_confidence_score = Column(Float,   default=0.0)
    voice_stability        = Column(Float,   default=0.0)
    nervousness_detected   = Column(Boolean, default=False)

    # Response quality
    relevance_score        = Column(Float,   default=0.0)
    completeness_score     = Column(Float,   default=0.0)

    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    interview = relationship("Interview", back_populates="metrics")

    def __repr__(self):
        return f"<InterviewMetric(id={self.id}, interview_id={self.interview_id})>"