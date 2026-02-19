"""
Voice Interview WebSocket Handler.
backend/app/websocket/voice_interview_handler.py
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
from app.services.interview.interview_service import InterviewService
from app.services.interview.question_generator import QuestionGeneratorService
from app.services.realtime.realtime_client import RealtimeAPIClient
from app.services.recording.event_logger import EventLogger


class VoiceInterviewHandler:

    def __init__(self):
        self.interview_service = InterviewService()
        self.question_generator = QuestionGeneratorService()

    async def handle(self, websocket: WebSocket, session_id: str, user_id: int):
        await websocket.accept()
        db = SessionLocal()
        realtime_client = None

        try:
            # Load session
            interview = self.interview_service._get_session(db, session_id, user_id)
            
            if interview.status == InterviewStatus.CANCELLED:
                await self._send(websocket, {"type": "error", "message": "Session cancelled"})
                return

            # Generate questions
            resume = interview.resume
            job_role = interview.job_role or "Software Engineer"
            skills = resume.skills if resume else []
            exp_years = resume.experience_years if resume else None

            questions = await self.question_generator.generate_questions(
                job_role=job_role,
                skills=skills,
                experience_years=exp_years,
                interview_type=interview.interview_type or "job_role",
                num_questions=20  # Generate pool of questions
            )

            # Start interview
            self.interview_service.start_session(db, session_id, user_id)

            # Connect to Realtime API
            realtime_client = RealtimeAPIClient()
            await realtime_client.connect()

            # Set up audio callback
            async def on_audio(audio_b64: str):
                await self._send(websocket, {
                    "type": "ai_audio",
                    "audio": audio_b64
                })

            async def on_done():
                await self._send(websocket, {
                    "type": "ai_done_speaking"
                })

            realtime_client.on_audio_callback = on_audio
            realtime_client.on_done_callback = on_done

            # State
            state = {
                "current_question_index": 0,
                "questions_asked": [],
                "responses": [],
                "start_time": time.time(),
                "ended": False,
                "wrap_up_initiated": False,
                "ai_speaking": False
            }

            # Send ready
            await self._send(websocket, {
                "type": "ready",
                "session_id": session_id,
                "job_role": job_role
            })

            # AI Introduction
            intro = f"Hello! I'm your AI interviewer today. I'll ask you several questions about your experience as a {job_role}. Please answer using your microphone. Take your time with each answer. Let's begin."
            await realtime_client.speak_text(intro)
            state["ai_speaking"] = True
            
            # Wait a bit, then ask first question
            await asyncio.sleep(2)
            await self._ask_question(websocket, realtime_client, questions, state)

            # Main loop
            while not state["ended"]:
                elapsed = time.time() - state["start_time"]

                # Receive message from client
                try:
                    raw = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                    message = json.loads(raw)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break

                msg_type = message.get("type")

                # Candidate finished speaking
                if msg_type == "response_complete":
                    response_text = message.get("transcript", "")
                    
                    state["responses"].append({
                        "question_index": state["current_question_index"] - 1,
                        "response": response_text,
                        "timestamp": datetime.utcnow().isoformat()
                    })

                    # Decide: ask next or wrap up?
                    if elapsed < 450:  # Before 7:30
                        await asyncio.sleep(1.5)
                        await self._ask_question(websocket, realtime_client, questions, state)
                    else:  # After 7:30, wrap up
                        if not state["wrap_up_initiated"]:
                            await self._wrap_up(websocket, realtime_client, db, interview, state, questions)
                            state["ended"] = True

                # Manual end
                elif msg_type == "end":
                    await self._wrap_up(websocket, realtime_client, db, interview, state, questions)
                    state["ended"] = True

            # Save final data
            self.interview_service.end_session(
                db=db,
                session_id=session_id,
                user_id=user_id,
                questions_asked=state["questions_asked"],
                responses_given=state["responses"]
            )

        except Exception as e:
            print(f"Voice interview error: {e}")
            await self._send(websocket, {"type": "error", "message": str(e)})

        finally:
            if realtime_client:
                await realtime_client.close()
            db.close()
            try:
                await websocket.close()
            except Exception:
                pass

    async def _ask_question(self, websocket, realtime_client, questions, state):
        idx = state["current_question_index"]
        
        if idx >= len(questions):
            return

        question_data = questions[idx]
        question_text = question_data["question"]
        
        state["questions_asked"].append(question_text)
        state["current_question_index"] += 1

        # Send question text to frontend
        await self._send(websocket, {
            "type": "question",
            "text": question_text,
            "index": idx + 1
        })

        # AI speaks the question
        await realtime_client.speak_text(question_text)

    async def _wrap_up(self, websocket, realtime_client, db, interview, state, questions):
        state["wrap_up_initiated"] = True
        
        closing = "Thank you for that answer. That wraps up our interview today. You did great! I'm now generating your personalized feedback report."
        await realtime_client.speak_text(closing)
        
        await asyncio.sleep(3)
        
        await self._send(websocket, {
            "type": "ended",
            "interview_id": interview.id,
            "total_questions": len(state["questions_asked"]),
            "message": "Interview complete"
        })

    async def _send(self, websocket: WebSocket, data: dict):
        try:
            await websocket.send_text(json.dumps(data))
        except Exception:
            pass
