"""
Resume schemas for API validation.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ResumeUploadResponse(BaseModel):
    """Returned immediately after upload + parse"""
    resume_id:        int
    filename:         str
    blob_url:         str
    file_size:        int
    job_role:         Optional[str]         = None
    skills:           Optional[List[str]]   = None
    experience_years: Optional[int]         = None
    parsed_data:      Optional[Dict[str, Any]] = None
    uploaded_at:      datetime

    model_config = {"from_attributes": True}


class ResumeResponse(BaseModel):
    """Full resume details"""
    id:               int
    user_id:          int
    filename:         str
    blob_url:         str
    file_size:        int
    job_role:         Optional[str]            = None
    experience_years: Optional[int]            = None
    skills:           Optional[List[str]]      = None
    parsed_data:      Optional[Dict[str, Any]] = None
    uploaded_at:      datetime

    model_config = {"from_attributes": True}