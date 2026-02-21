"""
WORKING VERSION with detailed logging
REPLACE: backend/app/websocket/voice_interview_handler.py
"""
import json
import asyncio
import time
from datetime import datetime
from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.interview import InterviewStatus
from app.services.interview.interview_service import InterviewService
from app.services.interview.question_generator import QuestionGeneratorService
from app.services.realtime.realtime_client import RealtimeAPIClient


class VoiceInterviewHandler:

    def __init__(self):
        self.interview_service = InterviewService()
        self.question_generator = QuestionGeneratorService()

    async def handle(self, websocket: WebSocket, session_id: str, user_id: int):
        print("\n" + "="*80)
        print("[INTERVIEW] Starting new interview")
        print("="*80 + "\n")
        
        await websocket.accept()
        db = SessionLocal()
        realtime_client = None

        try:
            interview = self.interview_service._get_session(db, session_id, user_id)
            resume = interview.resume
            job_role = interview.job_role or "Software Engineer"
            
            questions = await self.question_generator.generate_questions(
                job_role=job_role,
                skills=resume.skills if resume else [],
                experience_years=resume.experience_years if resume else None,
                interview_type=interview.interview_type or "job_role",
                num_questions=10
            )

            print(f"[INTERVIEW] Generated {len(questions)} questions")

            self.interview_service.start_session(db, session_id, user_id)

            # Connect Realtime API
            realtime_client = RealtimeAPIClient()
            if not await realtime_client.connect():
                print("[INTERVIEW] Failed to connect to Realtime API")
                return

            # Callbacks with logging
            async def on_audio(audio_b64: str):
                await self._send(websocket, {"type": "ai_audio", "audio": audio_b64})

            async def on_transcript(text: str):
                print(f"[AI SPEAKING] {text}", end="", flush=True)
                await self._send(websocket, {"type": "ai_transcript_delta", "text": text})

            async def on_done():
                print("\n[AI] Done speaking\n")
                await self._send(websocket, {"type": "ai_done_speaking"})

            realtime_client.on_audio_callback = on_audio
            realtime_client.on_transcript_callback = on_transcript
            realtime_client.on_done_callback = on_done

            state = {
                "current_question_index": 0,
                "questions_asked": [],
                "responses": [],
                "start_time": time.time(),
                "ended": False,
                "waiting_for_candidate": False
            }

            await self._send(websocket, {"type": "ready", "session_id": session_id})

            # Intro
            intro = f"Hello! I'm your AI interviewer. I'll ask you questions about {job_role}. Let's begin."
            print(f"\n[AI INTRO] {intro}\n")
            await realtime_client.speak_text(intro)
            
            await asyncio.sleep(12)
            
            # Ask first question
            await self._ask_question(websocket, realtime_client, questions, state)
            state["waiting_for_candidate"] = True

            # Main loop
            while not state["ended"]:
                elapsed = time.time() - state["start_time"]

                try:
                    raw = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                    message = json.loads(raw)
                except asyncio.TimeoutError:
                    if elapsed > 480:
                        state["ended"] = True
                    continue
                except:
                    break

                msg_type = message.get("type")

                if msg_type == "response_complete" and state["waiting_for_candidate"]:
                    response_text = message.get("transcript", "").strip()
                    
                    if not response_text:
                        continue
                    
                    print(f"\n[CANDIDATE ANSWER] {response_text}\n")
                    
                    state["responses"].append({
                        "question_index": state["current_question_index"] - 1,
                        "response": response_text
                    })

                    state["waiting_for_candidate"] = False
                    
                    await asyncio.sleep(3)
                    
                    if elapsed < 450 and state["current_question_index"] < len(questions):
                        await self._ask_question(websocket, realtime_client, questions, state)
                        state["waiting_for_candidate"] = True
                    else:
                        await self._wrap_up(websocket, realtime_client, interview)
                        state["ended"] = True

                elif msg_type == "end":
                    print("\n[INTERVIEW] Candidate ended interview\n")
                    await self._wrap_up(websocket, realtime_client, interview)
                    state["ended"] = True

            # Save
            self.interview_service.end_session(
                db=db,
                session_id=session_id,
                user_id=user_id,
                questions_asked=state["questions_asked"],
                responses_given=state["responses"]
            )

            print("\n" + "="*80)
            print("[INTERVIEW] Interview completed")
            print("="*80 + "\n")

        except Exception as e:
            print(f"\n[ERROR] {e}\n")
            import traceback
            traceback.print_exc()

        finally:
            if realtime_client:
                await realtime_client.close()
            db.close()
            try:
                await websocket.close()
            except:
                pass

    async def _ask_question(self, websocket, realtime_client, questions, state):
        idx = state["current_question_index"]
        
        if idx >= len(questions):
            return

        question_text = questions[idx]["question"]
        state["questions_asked"].append(question_text)
        state["current_question_index"] += 1

        print(f"\n{'='*80}")
        print(f"[QUESTION {idx + 1}] {question_text}")
        print('='*80 + "\n")

        await self._send(websocket, {"type": "question", "index": idx + 1})
        await realtime_client.speak_text(question_text)
        await asyncio.sleep(15)

    async def _wrap_up(self, websocket, realtime_client, interview):
        closing = "Thank you! Generating your feedback now."
        print(f"\n[AI CLOSING] {closing}\n")
        await realtime_client.speak_text(closing)
        await asyncio.sleep(8)
        
        await self._send(websocket, {"type": "ended", "interview_id": interview.id})

    async def _send(self, websocket: WebSocket, data: dict):
        try:
            await websocket.send_text(json.dumps(data))
        except:
            pass