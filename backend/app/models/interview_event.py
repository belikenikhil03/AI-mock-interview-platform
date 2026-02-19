"""
Interview Event model - stores timeline events with timestamps.
backend/app/models/interview_event.py
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class InterviewEvent(Base):
    __tablename__ = "interview_events"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    timestamp_seconds = Column(Float, nullable=False)  # e.g., 103.250 = 1:43.25
    event_type = Column(String(50), nullable=False)  # 'filler_word', 'low_eye_contact', etc.
    event_data = Column(Text, nullable=True)  # JSON string
    severity = Column(String(20), default="info")  # 'info', 'warning', 'critical'
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    interview = relationship("Interview", back_populates="events")