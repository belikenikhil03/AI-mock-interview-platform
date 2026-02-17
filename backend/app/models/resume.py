"""resume.py - Resume model"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename       = Column(String(255), nullable=False)
    blob_url       = Column(String(500), nullable=False)
    file_size      = Column(Integer, nullable=False)
    parsed_data    = Column(JSON,  nullable=True)
    extracted_text = Column(Text,  nullable=True)
    job_role       = Column(String(255), nullable=True)
    experience_years = Column(Integer,  nullable=True)
    skills         = Column(JSON,  nullable=True)
    uploaded_at    = Column(DateTime(timezone=True), server_default=func.now())

    user       = relationship("User",      back_populates="resumes")
    interviews = relationship("Interview", back_populates="resume")

    def __repr__(self):
        return f"<Resume(id={self.id}, filename='{self.filename}')>"