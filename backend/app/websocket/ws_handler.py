"""
WebSocket Interview Handler.
Manages the real-time interview session:
- Connects to Azure OpenAI Realtime API
- Streams AI audio to candidate
- Receives candidate audio/text
- Tracks metrics in real-time
- Auto-ends after MAX_INTERVIEW_DURATION_MINUTES
"""
import json
import asyncio
import time
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.interview import InterviewStatus
from app.models.metric import InterviewMetric
from app.services.interview.interview_service import InterviewService
from app.services.interview.question_generator import QuestionGeneratorService


class InterviewWebSocketHandler:

    def __init__(self):
        self.interview_service  = InterviewService()
        self.question_generator = QuestionGeneratorService()

    async def handle(self, websocket: WebSocket, session_id: str, user_id: int):
        """
        Main WebSocket handler for a live interview session.

        Message protocol (client → server):
        { "type": "start" }                          - start the interview
        { "type": "audio", "data": "<base64>" }      - audio chunk from mic
        { "type": "text",  "data": "response text" } - text fallback
        { "type": "video_metrics", "eye_contact": 0.8, "fidgeting": 2 }
        { "type": "end" }                             - candidate ends early

        Message protocol (server → client):
        { "type": "ready",    "session_id": "...", "job_role": "..." }
        { "type": "question", "text": "...", "index": 1, "total": 8 }
        { "type": "metrics",  "filler_words": 3, "eye_contact": 0.75, ... }
        { "type": "warning",  "message": "2 minutes remaining" }
        { "type": "ended",    "reason": "completed|timeout|silence" }
        { "type": "error",    "message": "..." }
        """
        await websocket.accept()
        db = SessionLocal()

        try:
            # ── Load session ──────────────────────────────────────────────────
            interview = self.interview_service._get_session(db, session_id, user_id)

            if interview.status == InterviewStatus.CANCELLED:
                await self._send(websocket, {"type": "error", "message": "Session was cancelled"})
                return

            # ── Load resume data for question generation ──────────────────────
            resume     = interview.resume
            job_role   = interview.job_role or "Software Engineer"
            skills     = resume.skills          if resume else []
            exp_years  = resume.experience_years if resume else None

            # ── Generate questions ────────────────────────────────────────────
            questions = await self.question_generator.generate_questions(
                job_role       = job_role,
                skills         = skills,
                experience_years = exp_years,
                interview_type = interview.interview_type or "job_role"
            )

            # ── Start session ─────────────────────────────────────────────────
            self.interview_service.start_session(db, session_id, user_id)

            # Send ready signal to client
            await self._send(websocket, {
                "type":       "ready",
                "session_id": session_id,
                "job_role":   job_role,
                "total_questions": len(questions),
                "duration_minutes": settings.MAX_INTERVIEW_DURATION_MINUTES
            })

            # ── Track state ───────────────────────────────────────────────────
            state = {
                "current_question_index": 0,
                "questions_asked":        [],
                "responses":              [],
                "filler_words_count":     0,
                "total_words":            0,
                "pauses":                 [],
                "last_speech_time":       time.time(),
                "eye_contact_scores":     [],
                "fidgeting_events":       0,
                "start_time":             time.time(),
                "ended":                  False
            }

            max_duration = settings.MAX_INTERVIEW_DURATION_MINUTES * 60
            max_silence  = settings.MAX_SILENCE_DURATION_SECONDS
            filler_words = {
                "um", "uh", "like", "you know", "basically", "literally",
                "actually", "so", "right", "okay", "hmm", "er", "ah"
            }

            # ── Ask first question ────────────────────────────────────────────
            await self._ask_question(websocket, questions, state)

            # ── Main message loop ─────────────────────────────────────────────
            while not state["ended"]:

                # Check time limits
                elapsed = time.time() - state["start_time"]
                silence = time.time() - state["last_speech_time"]

                if elapsed >= max_duration:
                    await self._end_interview(
                        websocket, db, interview, state, questions, "timeout"
                    )
                    break

                if silence >= max_silence:
                    await self._end_interview(
                        websocket, db, interview, state, questions, "silence"
                    )
                    break

                # Send time warning at 2 minutes remaining
                remaining = max_duration - elapsed
                if 115 <= remaining <= 125:
                    await self._send(websocket, {
                        "type":    "warning",
                        "message": "2 minutes remaining"
                    })

                # Receive message from client
                try:
                    raw = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=5.0
                    )
                    message = json.loads(raw)

                except asyncio.TimeoutError:
                    # No message — just continue loop (check time limits)
                    continue

                except WebSocketDisconnect:
                    # Client disconnected
                    await self._end_interview(
                        websocket, db, interview, state, questions, "disconnected"
                    )
                    break

                msg_type = message.get("type")

                # ── Handle client messages ────────────────────────────────────
                if msg_type == "text":
                    # Candidate spoke — process response
                    response_text = message.get("data", "")
                    state["last_speech_time"] = time.time()

                    # Count words and filler words
                    words = response_text.lower().split()
                    state["total_words"] += len(words)
                    for fw in filler_words:
                        state["filler_words_count"] += response_text.lower().count(fw)

                    # Store response
                    if state["current_question_index"] <= len(questions):
                        state["responses"].append({
                            "question_index": state["current_question_index"] - 1,
                            "response":       response_text,
                            "timestamp":      datetime.utcnow().isoformat()
                        })

                    # Send updated metrics to client
                    await self._send_metrics(websocket, state, elapsed)

                    # Move to next question if response received
                    if state["current_question_index"] < len(questions):
                        await asyncio.sleep(1.5)  # brief pause between Q&A
                        await self._ask_question(websocket, questions, state)
                    else:
                        # All questions done
                        await self._end_interview(
                            websocket, db, interview, state, questions, "completed"
                        )
                        break

                elif msg_type == "video_metrics":
                    # Receive MediaPipe metrics from frontend
                    eye_contact = message.get("eye_contact", 0.0)
                    fidgeting   = message.get("fidgeting",   0)

                    state["eye_contact_scores"].append(eye_contact)
                    state["fidgeting_events"]  += fidgeting

                elif msg_type == "end":
                    # Candidate ends early
                    await self._end_interview(
                        websocket, db, interview, state, questions, "candidate_ended"
                    )
                    break

            # ── Save metrics to DB ────────────────────────────────────────────
            await self._save_metrics(db, interview.id, state)

        except Exception as e:
            print(f"WebSocket error: {e}")
            await self._send(websocket, {
                "type":    "error",
                "message": f"Session error: {str(e)}"
            })

        finally:
            db.close()
            try:
                await websocket.close()
            except Exception:
                pass

    async def _ask_question(self, websocket: WebSocket, questions: list, state: dict):
        """Send the next question to the client."""
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
        """Send real-time metrics update to client."""
        eye_avg = (
            sum(state["eye_contact_scores"]) / len(state["eye_contact_scores"])
            if state["eye_contact_scores"] else 0.0
        )

        await self._send(websocket, {
            "type":                "metrics",
            "filler_words_count":  state["filler_words_count"],
            "total_words":         state["total_words"],
            "eye_contact":         round(eye_avg, 2),
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
        reason: str,
        questions: list = None
    ):
        """Gracefully end the interview and notify client."""
        state["ended"] = True

        # End session in DB
        self.interview_service.end_session(
            db             = db,
            session_id     = interview.session_id,
            user_id        = interview.user_id,
            questions_asked = state["questions_asked"],
            responses_given = state["responses"]
        )

        # Notify client
        await self._send(websocket, {
            "type":              "ended",
            "reason":            reason,
            "total_questions":   len(state["questions_asked"]),
            "total_words":       state["total_words"],
            "filler_words":      state["filler_words_count"],
            "duration_seconds":  int(time.time() - state["start_time"]),
            "message":           self._end_message(reason)
        })

    def _end_message(self, reason: str) -> str:
        messages = {
            "completed":       "Great job! You've completed the interview. Generating feedback...",
            "timeout":         "Time's up! Great effort. Generating feedback...",
            "silence":         "Session ended due to inactivity. Generating feedback...",
            "candidate_ended": "Interview ended. Generating feedback...",
            "disconnected":    "Connection lost. Your progress has been saved."
        }
        return messages.get(reason, "Interview ended.")

    async def _save_metrics(self, db: Session, interview_id: int, state: dict):
        """Persist aggregated metrics to DB."""
        try:
            eye_avg = (
                sum(state["eye_contact_scores"]) / len(state["eye_contact_scores"])
                if state["eye_contact_scores"] else 0.0
            )

            metric = InterviewMetric(
                interview_id           = interview_id,
                filler_words_count     = state["filler_words_count"],
                total_words_spoken     = state["total_words"],
                eye_contact_percentage = round(eye_avg * 100, 1),
                fidgeting_count        = state["fidgeting_events"],
            )
            db.add(metric)
            db.commit()
        except Exception as e:
            print(f"Failed to save metrics: {e}")

    async def _send(self, websocket: WebSocket, data: dict):
        """Send JSON message to client."""
        try:
            await websocket.send_text(json.dumps(data))
        except Exception:
            pass  # client may have disconnected
