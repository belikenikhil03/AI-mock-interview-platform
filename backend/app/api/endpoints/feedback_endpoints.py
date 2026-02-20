"""
Feedback API endpoints.
Trigger feedback generation and retrieve results.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import json

from app.core.database import get_db
from app.api.dependencies.deps import get_current_user
from app.api.schemas.feedback import FeedbackResponse
from app.services.feedback.feedback_service import FeedbackService
from app.models.user import User
from app.models.interview import Interview

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

@router.get("/{interview_id}/with-timeline", summary="Get feedback with video timeline")
async def get_feedback_with_timeline(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get feedback along with video timeline for playback."""
    from app.services.recording.event_logger import EventLogger
    from app.services.storage.storage_service import StorageService  # ADD THIS
    
    # Get feedback
    service = FeedbackService()
    feedback = service.get_feedback(db, interview_id, current_user.id)
    
    # Get interview
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id
    ).first()
    
    # Get timeline events
    events = EventLogger.get_timeline(db, interview_id)
    grouped = EventLogger.group_nearby_events(events, time_window=5.0)
    
    # Generate SAS URL for video (ADD THIS BLOCK)
    video_url = None
    if interview.video_blob_url:
        storage = StorageService()
        video_url = storage.get_video_sas_url(interview.video_blob_url, expiry_hours=24)
    
    return {
        "feedback": {
            "id": feedback.id,
            "interview_id": feedback.interview_id,
            "overall_score": feedback.overall_score,
            "content_score": feedback.content_score,
            "communication_score": feedback.communication_score,
            "confidence_score": feedback.confidence_score,
            "what_went_right": feedback.what_went_right,
            "what_went_wrong": feedback.what_went_wrong,
            "strengths": feedback.strengths,
            "weaknesses": feedback.weaknesses,
            "detailed_feedback": feedback.detailed_feedback,
            "improvement_suggestions": feedback.improvement_suggestions
        },
        "video": {
            "url": video_url,  # CHANGED: Now SAS URL instead of blob URL
            "duration_seconds": interview.video_duration_seconds,
            "total_events": len(events)
        },
        "timeline": [
            {
                "start_time": group[0].timestamp_seconds,
                "end_time": group[-1].timestamp_seconds,
                "count": len(group),
                "events": [
                    {
                        "timestamp": e.timestamp_seconds,
                        "type": e.event_type,
                        "data": json.loads(e.event_data) if e.event_data else {},
                        "severity": e.severity
                    }
                    for e in group
                ]
            }
            for group in grouped
        ]
    }