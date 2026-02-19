"""
Recording upload endpoint.
backend/app/api/endpoints/recordings.py
"""
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies.deps import get_current_user
from app.services.storage.storage_service import StorageService
from app.services.recording.event_logger import EventLogger
from app.models.interview import Interview
from app.models.user import User
import json

router = APIRouter()


@router.post("/interviews/{interview_id}/upload-recording")
async def upload_recording(
    interview_id: int,
    video: UploadFile = File(...),
    timeline: str = Form(...),
    duration: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload video recording and timeline events.
    
    Args:
        interview_id: Interview ID
        video: Video file (WebM)
        timeline: JSON string of events array
        duration: Video duration in seconds
    """
    # Verify ownership
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Upload video to Azure Blob
    storage = StorageService()
    blob_url = storage.upload_video(
        video.file,
        f"interviews/user_{current_user.id}/interview_{interview_id}/recording.webm"
    )
    
    # Parse and save events
    try:
        events = json.loads(timeline)
        EventLogger.log_batch_events(db, interview_id, events)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid timeline JSON")
    
    # Update interview record
    interview.video_blob_url = blob_url
    interview.video_duration_seconds = duration
    interview.total_events_count = len(events)
    db.commit()
    
    return {
        "status": "success",
        "video_url": blob_url,
        "events_saved": len(events),
        "duration_seconds": duration
    }


@router.get("/interviews/{interview_id}/timeline")
async def get_timeline(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get timeline events for an interview.
    """
    # Verify ownership
    interview = db.query(Interview).filter(
        Interview.id == interview_id,
        Interview.user_id == current_user.id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    # Get all events
    events = EventLogger.get_timeline(db, interview_id)
    
    # Group nearby events (within 5 seconds)
    grouped = EventLogger.group_nearby_events(events, time_window=5.0)
    
    return {
        "interview_id": interview_id,
        "video_url": interview.video_blob_url,
        "duration_seconds": interview.video_duration_seconds,
        "total_events": len(events),
        "grouped_events": [
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
