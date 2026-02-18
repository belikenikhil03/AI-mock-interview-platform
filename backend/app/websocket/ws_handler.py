"""
WebSocket Interview Handler with ML Analyzers integrated.
Now uses AudioAnalyzer for real filler word detection and speech analysis.
"""
import json
import asyncio
import time
from datetime import datetime
from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.interview import InterviewStatus
from app.models.metric import InterviewMetric
from app.services.interview.interview_service import InterviewService
from app.services.interview.question_generator import QuestionGeneratorService
from app.services.ml.audio_analyzer import AudioAnalyzer


class InterviewWebSocketHandler:

    def __init__(self):
        self.interview_service  = InterviewService()
        self.question_generator = QuestionGeneratorService()
        self.audio_analyzer     = AudioAnalyzer()

    async def handle(self, websocket: WebSocket, session_id: str, user_id: int):
        await websocket.accept()
        db = SessionLocal()

        try:
            interview = self.interview_service._get_session(db, session_id, user_id)

            if interview.status == InterviewStatus.CANCELLED:
                await self._send(websocket, {"type": "error", "message": "Session was cancelled"})
                return

            resume     = interview.resume
            job_role   = interview.job_role or "Software Engineer"
            skills     = resume.skills if resume else []
            exp_years  = resume.experience_years if resume else None

            questions = await self.question_generator.generate_questions(
                job_role=job_role,
                skills=skills,
                experience_years=exp_years,
                interview_type=interview.interview_type or "job_role"
            )

            self.interview_service.start_session(db, session_id, user_id)

            await self._send(websocket, {
                "type":            "ready",
                "session_id":      session_id,
                "job_role":        job_role,
                "total_questions": len(questions),
                "duration_minutes": settings.MAX_INTERVIEW_DURATION_MINUTES
            })

            state = {
                "current_question_index": 0,
                "questions_asked":        [],
                "responses":              [],
                "response_timestamps":    [],  # Track timing for pause analysis
                "filler_words_count":     0,
                "total_words":            0,
                "speech_samples":         [],  # For speech rate calculation
                "eye_contact_scores":     [],
                "fidgeting_events":       0,
                "movement_history":       [],
                "start_time":             time.time(),
                "ended":                  False
            }

            max_duration = settings.MAX_INTERVIEW_DURATION_MINUTES * 60
            max_silence  = settings.MAX_SILENCE_DURATION_SECONDS

            # Ask first question
            await self._ask_question(websocket, questions, state)

            # Main loop
            while not state["ended"]:
                elapsed = time.time() - state["start_time"]

                # Check end conditions
                if elapsed >= max_duration:
                    await self._end_interview(websocket, db, interview, state, questions, "timeout")
                    break

                if state["current_question_index"] >= len(questions):
                    await self._end_interview(websocket, db, interview, state, questions, "completed")
                    break

                # Time warning
                remaining = max_duration - elapsed
                if 115 <= remaining <= 125:
                    await self._send(websocket, {"type": "warning", "message": "2 minutes remaining"})

                # Receive message
                try:
                    raw = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                    message = json.loads(raw)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    await self._end_interview(websocket, db, interview, state, questions, "disconnected")
                    break

                msg_type = message.get("type")

                # Handle text response
                if msg_type == "text":
                    response_text = message.get("data", "")
                    timestamp = time.time()

                    # Use AudioAnalyzer to analyze the response
                    analysis = self.audio_analyzer.analyze_text(response_text)

                    # Update state with analyzed data
                    state["filler_words_count"] += analysis["filler_words_count"]
                    state["total_words"] += analysis["total_words"]
                    state["speech_samples"].append({
                        "words": analysis["total_words"],
                        "fillers": analysis["filler_words_count"],
                        "timestamp": timestamp
                    })

                    # Store response
                    if state["current_question_index"] <= len(questions):
                        state["responses"].append({
                            "question_index": state["current_question_index"] - 1,
                            "response":       response_text,
                            "timestamp":      datetime.utcnow().isoformat(),
                            "word_count":     analysis["total_words"],
                            "filler_count":   analysis["filler_words_count"]
                        })
                        state["response_timestamps"].append(timestamp)

                    await self._send_metrics(websocket, state, elapsed)

                    # Move to next question
                    if state["current_question_index"] < len(questions):
                        await asyncio.sleep(1.5)
                        await self._ask_question(websocket, questions, state)
                    else:
                        await self._end_interview(websocket, db, interview, state, questions, "completed")
                        break

                # Handle video metrics from client
                elif msg_type == "video_metrics":
                    eye_contact = message.get("eye_contact", 0.0)
                    movement    = message.get("movement", 0.0)
                    fidgeting   = message.get("fidgeting", 0)

                    state["eye_contact_scores"].append(eye_contact)
                    state["movement_history"].append(movement)
                    state["fidgeting_events"] += fidgeting

                # Handle end button
                elif msg_type == "end":
                    await self._end_interview(websocket, db, interview, state, questions, "candidate_ended")
                    break

            await self._save_metrics(db, interview.id, state)

        except Exception as e:
            print(f"WebSocket error: {e}")
            await self._send(websocket, {"type": "error", "message": f"Session error: {str(e)}"})

        finally:
            db.close()
            try:
                await websocket.close()
            except Exception:
                pass

    async def _ask_question(self, websocket: WebSocket, questions: list, state: dict):
        idx = state["current_question_index"]
        if idx >= len(questions):
            return

        question_data = questions[idx]
        state["questions_asked"].append(question_data["question"])
        state["current_question_index"] += 1

        await self._send(websocket, {
            "type":     "question",
            "text":     question_data["question"],
            "index":    idx + 1,
            "total":    len(questions),
            "category": question_data.get("category", "general")
        })

    async def _send_metrics(self, websocket: WebSocket, state: dict, elapsed: float):
        # Calculate speech rate
        speech_rate = 0
        if state["speech_samples"] and elapsed > 0:
            total_words = sum(s["words"] for s in state["speech_samples"])
            speech_rate = (total_words / elapsed) * 60  # WPM

        # Calculate average eye contact
        eye_avg = (
            sum(state["eye_contact_scores"]) / len(state["eye_contact_scores"])
            if state["eye_contact_scores"] else 0.0
        )

        await self._send(websocket, {
            "type":                "metrics",
            "filler_words_count":  state["filler_words_count"],
            "total_words":         state["total_words"],
            "speech_rate_wpm":     round(speech_rate, 1),
            "eye_contact":         round(eye_avg * 100, 1),
            "fidgeting_count":     state["fidgeting_events"],
            "elapsed_seconds":     int(elapsed),
            "questions_answered":  state["current_question_index"] - 1
        })

    async def _end_interview(
        self,
        websocket: WebSocket,
        db: Session,
        interview,
        state: dict,
        questions: list,
        reason: str
    ):
        state["ended"] = True

        self.interview_service.end_session(
            db              = db,
            session_id      = interview.session_id,
            user_id         = interview.user_id,
            questions_asked = state["questions_asked"],
            responses_given = state["responses"]
        )

        await self._send(websocket, {
            "type":              "ended",
            "reason":            reason,
            "interview_id":      interview.id,
            "total_questions":   len(state["questions_asked"]),
            "total_words":       state["total_words"],
            "filler_words":      state["filler_words_count"],
            "duration_seconds":  int(time.time() - state["start_time"]),
            "message":           self._end_message(reason)
        })

    def _end_message(self, reason: str) -> str:
        messages = {
            "completed":       "Great job! You've completed the interview.",
            "timeout":         "Time's up! Great effort.",
            "silence":         "Session ended due to inactivity.",
            "candidate_ended": "Interview ended.",
            "disconnected":    "Connection lost. Your progress has been saved."
        }
        return messages.get(reason, "Interview ended.")

    async def _save_metrics(self, db: Session, interview_id: int, state: dict):
        try:
            # Calculate aggregated metrics
            eye_avg = (
                sum(state["eye_contact_scores"]) / len(state["eye_contact_scores"])
                if state["eye_contact_scores"] else 0.0
            )

            # Calculate pause metrics
            pause_analysis = self.audio_analyzer.detect_pauses(
                [(i, "") for i, _ in enumerate(state["response_timestamps"])]
            )

            # Calculate speech rate
            duration = time.time() - state["start_time"]
            speech_rate = (state["total_words"] / duration * 60) if duration > 0 else 0

            metric = InterviewMetric(
                interview_id           = interview_id,
                filler_words_count     = state["filler_words_count"],
                total_words_spoken     = state["total_words"],
                average_pause_duration = pause_analysis.get("avg_pause_duration", 0.0),
                longest_pause_duration = pause_analysis.get("max_pause_duration", 0.0),
                speech_rate_wpm        = round(speech_rate, 1),
                eye_contact_percentage = round(eye_avg * 100, 1),
                fidgeting_count        = state["fidgeting_events"],
            )
            db.add(metric)
            db.commit()
        except Exception as e:
            print(f"Failed to save metrics: {e}")

    async def _send(self, websocket: WebSocket, data: dict):
        try:
            await websocket.send_text(json.dumps(data))
        except Exception:
            pass