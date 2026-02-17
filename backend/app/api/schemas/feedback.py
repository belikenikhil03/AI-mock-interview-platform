"""Feedback schemas for API validation."""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class FeedbackResponse(BaseModel):
    id:                     int
    interview_id:           int
    content_score:          Optional[float] = None
    communication_score:    Optional[float] = None
    confidence_score:       Optional[float] = None
    overall_score:          Optional[float] = None
    what_went_right:        Optional[List[Dict[str, Any]]] = None
    what_went_wrong:        Optional[List[Dict[str, Any]]] = None
    strengths:              Optional[List[str]] = None
    weaknesses:             Optional[List[str]] = None
    detailed_feedback:      Optional[str] = None
    improvement_suggestions: Optional[List[str]] = None

    model_config = {"from_attributes": True}