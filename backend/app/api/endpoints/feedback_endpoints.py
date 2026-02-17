"""
Feedback API endpoints.
Trigger feedback generation and retrieve results.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies.deps import get_current_user
from app.api.schemas.feedback import FeedbackResponse
from app.services.feedback.feedback_service import FeedbackService
from app.models.user import User

router = APIRouter()


@router.post(
    "/{interview_id}/generate",
    response_model=FeedbackResponse,
    summary="Generate feedback for a completed interview"
)
async def generate_feedback(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger feedback generation for a completed interview.

    Pipeline:
    1. Calculates content, communication, confidence scores
    2. Categorizes metrics into what went right / wrong
    3. Generates GPT narrative feedback and improvement tips
    4. Saves and returns the full feedback report
    """
    service  = FeedbackService()
    feedback = await service.generate_feedback(db, interview_id, current_user.id)
    return feedback


@router.get(
    "/{interview_id}",
    response_model=FeedbackResponse,
    summary="Get feedback for an interview"
)
def get_feedback(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve already-generated feedback for an interview.
    Returns 404 if feedback hasn't been generated yet.
    """
    service  = FeedbackService()
    feedback = service.get_feedback(db, interview_id, current_user.id)
    return feedback
