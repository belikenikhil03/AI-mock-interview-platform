"""
WORKING VERSION - Simple realtime client
REPLACE: backend/app/services/realtime/realtime_client.py
"""
import asyncio
import json
import websockets
from typing import Callable, Optional, Dict
from app.core.config import settings


class RealtimeAPIClient:
    
    def __init__(self):
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.on_audio_callback: Optional[Callable] = None
        self.on_transcript_callback: Optional[Callable] = None
        self.on_done_callback: Optional[Callable] = None
        self.connected = False
        self.session_id = None
        self._listen_task = None
        self.is_speaking = False
        
    async def connect(self):
        try:
            base_url = settings.AZURE_OPENAI_ENDPOINT.rstrip("/").replace("https://", "wss://")
            deployment = settings.AZURE_OPENAI_DEPLOYMENT_NAME
            api_version = "2024-10-01-preview"
            
            url = f"{base_url}/openai/realtime?api-version={api_version}&deployment={deployment}"
            
            headers = {
                "api-key": settings.AZURE_OPENAI_API_KEY,
                "Content-Type": "application/json"
            }
            
            self.ws = await websockets.connect(
                url,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=20,
                close_timeout=10,
                max_size=10 * 1024 * 1024
            )
            
            self.connected = True
            print("[REALTIME] Connected")
            
            await self.configure_session()
            self._listen_task = asyncio.create_task(self._listen())
            
            return True
            
        except Exception as e:
            print(f"[REALTIME] Failed: {e}")
            self.connected = False
            return False
    
    async def configure_session(self):
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": "You are a professional interviewer. Speak one question at a time. Wait for responses.",
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": None,
                "temperature": 0.8
            }
        }
        
        await self.ws.send(json.dumps(config))
    
    async def _listen(self):
        try:
            async for message in self.ws:
                data = json.loads(message)
                await self._handle_message(data)
        except:
            self.connected = False
    
    async def _handle_message(self, data: Dict):
        msg_type = data.get("type", "")
        
        if msg_type == "session.created":
            self.session_id = data.get("session", {}).get("id")
        
        elif msg_type == "response.audio.delta":
            audio_b64 = data.get("delta", "")
            if audio_b64 and self.on_audio_callback:
                await self.on_audio_callback(audio_b64)
        
        elif msg_type == "response.audio_transcript.delta":
            text = data.get("delta", "")
            if text and self.on_transcript_callback:
                await self.on_transcript_callback(text)
        
        elif msg_type == "response.done":
            self.is_speaking = False
            if self.on_done_callback:
                await self.on_done_callback()
    
    async def speak_text(self, text: str):
        if not self.ws or not self.connected:
            raise Exception("Not connected")
        
        while self.is_speaking:
            await asyncio.sleep(0.1)
        
        self.is_speaking = True
        
        msg = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": text}]
            }
        }
        await self.ws.send(json.dumps(msg))
        
        response_msg = {
            "type": "response.create",
            "response": {"modalities": ["text", "audio"]}
        }
        await self.ws.send(json.dumps(response_msg))
    
    async def close(self):
        self.connected = False
        
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except:
                pass
        
        if self.ws:
            await self.ws.close()