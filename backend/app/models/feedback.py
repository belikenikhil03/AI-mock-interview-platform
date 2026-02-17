"""feedback.py - Feedback model"""
from sqlalchemy import Column, Integer, ForeignKey, Float, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id           = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False, unique=True, index=True)

    # Scores (0–100)
    content_score       = Column(Float, nullable=True)
    communication_score = Column(Float, nullable=True)
    confidence_score    = Column(Float, nullable=True)
    overall_score       = Column(Float, nullable=True)

    # Categorised results
    strengths               = Column(JSON, nullable=True)
    weaknesses              = Column(JSON, nullable=True)
    detailed_feedback       = Column(Text, nullable=True)
    improvement_suggestions = Column(JSON, nullable=True)
    what_went_right         = Column(JSON, nullable=True)
    what_went_wrong         = Column(JSON, nullable=True)

    interview = relationship("Interview", back_populates="feedback")

    def __repr__(self):
        return f"<Feedback(id={self.id}, interview_id={self.interview_id}, overall={self.overall_score})>"