"""
Event Logger - saves timeline events to database.
backend/app/services/recording/event_logger.py
"""
from sqlalchemy.orm import Session
from app.models.interview_event import InterviewEvent
import json


class EventLogger:
    
    @staticmethod
    def log_event(
        db: Session, 
        interview_id: int, 
        timestamp: float, 
        event_type: str, 
        data: dict = None, 
        severity: str = "info"
    ):
        """
        Log a single event to database.
        
        Args:
            db: Database session
            interview_id: Interview ID
            timestamp: Seconds from interview start (e.g., 103.250)
            event_type: Type of event ('filler_word', 'low_eye_contact', etc.)
            data: Event metadata as dict
            severity: 'info', 'warning', or 'critical'
        """
        event = InterviewEvent(
            interview_id=interview_id,
            timestamp_seconds=timestamp,
            event_type=event_type,
            event_data=json.dumps(data) if data else None,
            severity=severity
        )
        db.add(event)
        db.commit()
        return event
    
    @staticmethod
    def log_batch_events(db: Session, interview_id: int, events: list):
        """
        Log multiple events at once (more efficient).
        
        Args:
            events: List of dicts with keys: timestamp, type, data, severity
        """
        for event_data in events:
            event = InterviewEvent(
                interview_id=interview_id,
                timestamp_seconds=event_data.get("timestamp"),
                event_type=event_data.get("type"),
                event_data=json.dumps(event_data.get("data", {})),
                severity=event_data.get("severity", "info")
            )
            db.add(event)
        
        db.commit()
    
    @staticmethod
    def get_timeline(db: Session, interview_id: int):
        """
        Get all events for an interview, sorted by timestamp.
        """
        return db.query(InterviewEvent)\
            .filter(InterviewEvent.interview_id == interview_id)\
            .order_by(InterviewEvent.timestamp_seconds)\
            .all()
    
    @staticmethod
    def group_nearby_events(events: list, time_window: float = 5.0):
        """
        Group events that happen within time_window seconds.
        
        Args:
            events: List of InterviewEvent objects
            time_window: Seconds to group within (default 5.0)
        
        Returns:
            List of grouped events
        """
        if not events:
            return []
        
        grouped = []
        current_group = [events[0]]
        
        for i in range(1, len(events)):
            time_diff = events[i].timestamp_seconds - current_group[-1].timestamp_seconds
            
            if time_diff <= time_window:
                current_group.append(events[i])
            else:
                grouped.append(current_group)
                current_group = [events[i]]
        
        grouped.append(current_group)
        return grouped
