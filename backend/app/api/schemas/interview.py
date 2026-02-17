"""Interview schemas for API validation."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.interview import InterviewStatus


class InterviewCreate(BaseModel):
    resume_id:      Optional[int] = None
    interview_type: str = Field("job_role", max_length=100)


class InterviewResponse(BaseModel):
    id:               int
    session_id:       str
    user_id:          int
    resume_id:        Optional[int]      = None
    status:           InterviewStatus
    job_role:         Optional[str]      = None
    interview_type:   Optional[str]      = None
    duration_seconds: Optional[int]      = None
    started_at:       Optional[datetime] = None
    completed_at:     Optional[datetime] = None
    created_at:       datetime

    model_config = {"from_attributes": True}


class InterviewStartResponse(BaseModel):
    session_id:    str
    interview_id:  int
    websocket_url: str


class InterviewListResponse(BaseModel):
    interviews: List[InterviewResponse]
    total:      int