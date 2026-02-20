"""
Complete Azure OpenAI Realtime API Client with audio streaming.
REPLACE: backend/app/services/realtime/realtime_client.py
"""
import asyncio
import json
import websockets
import base64
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
        
    async def connect(self):
        """Connect to Azure OpenAI Realtime API WebSocket."""
        try:
            # Build WebSocket URL for Azure Realtime API
            base_url = settings.AZURE_OPENAI_ENDPOINT.rstrip("/").replace("https://", "wss://").replace("http://", "ws://")
            deployment = settings.AZURE_OPENAI_DEPLOYMENT_NAME
            api_version = "2024-10-01-preview"
            
            url = f"{base_url}/openai/realtime?api-version={api_version}&deployment={deployment}"
            
            headers = {
                "api-key": settings.AZURE_OPENAI_API_KEY,
                "Content-Type": "application/json"
            }
            
            print(f"Connecting to: {url[:50]}...")
            
            self.ws = await websockets.connect(
                url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            
            self.connected = True
            print("✅ Connected to Azure Realtime API")
            
            # Configure session
            await self.configure_session()
            
            # Start listening
            asyncio.create_task(self._listen())
            
            return True
            
        except Exception as e:
            print(f"❌ Realtime API connection failed: {e}")
            self.connected = False
            return False
    
    async def configure_session(self):
        """Configure the session with voice and instructions."""
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": "You are a professional job interviewer. Speak clearly, warmly, and naturally. Ask questions one at a time and wait for responses.",
                "voice": "alloy",  # Professional male voice
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "temperature": 0.7,
                "max_response_output_tokens": 4096
            }
        }
        
        await self.ws.send(json.dumps(config))
        print("✅ Session configured")
    
    async def _listen(self):
        """Listen for responses from Azure."""
        try:
            async for message in self.ws:
                data = json.loads(message)
                await self._handle_message(data)
                
        except websockets.exceptions.ConnectionClosed:
            print("Realtime API connection closed")
            self.connected = False
        except Exception as e:
            print(f"Realtime API listen error: {e}")
            self.connected = False
    
    async def _handle_message(self, data: Dict):
        """Handle incoming messages from Azure."""
        msg_type = data.get("type", "")
        
        # Session created
        if msg_type == "session.created":
            self.session_id = data.get("session", {}).get("id")
            print(f"Session created: {self.session_id}")
        
        # Audio delta (AI speaking)
        elif msg_type == "response.audio.delta":
            audio_b64 = data.get("delta", "")
            if audio_b64 and self.on_audio_callback:
                await self.on_audio_callback(audio_b64)
        
        # Transcript delta (AI text)
        elif msg_type == "response.text.delta":
            text = data.get("delta", "")
            if text and self.on_transcript_callback:
                await self.on_transcript_callback(text)
        
        # Response complete
        elif msg_type == "response.done":
            if self.on_done_callback:
                await self.on_done_callback()
        
        # Audio transcription from candidate
        elif msg_type == "conversation.item.input_audio_transcription.completed":
            transcript = data.get("transcript", "")
            print(f"Candidate said: {transcript}")
        
        # Errors
        elif msg_type == "error":
            error = data.get("error", {})
            print(f"❌ Realtime API error: {error}")
    
    async def send_text_message(self, text: str, role: str = "user"):
        """Send text message to conversation."""
        if not self.ws or not self.connected:
            raise Exception("Not connected to Realtime API")
        
        message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": role,
                "content": [
                    {
                        "type": "input_text",
                        "text": text
                    }
                ]
            }
        }
        
        await self.ws.send(json.dumps(message))
    
    async def request_response(self):
        """Request AI to generate response."""
        if not self.ws or not self.connected:
            raise Exception("Not connected to Realtime API")
        
        message = {
            "type": "response.create",
            "response": {
                "modalities": ["text", "audio"],
                "instructions": "Respond naturally and professionally as an interviewer."
            }
        }
        
        await self.ws.send(json.dumps(message))
    
    async def send_audio_chunk(self, audio_b64: str):
        """Send candidate's audio to Azure for processing."""
        if not self.ws or not self.connected:
            raise Exception("Not connected to Realtime API")
        
        message = {
            "type": "input_audio_buffer.append",
            "audio": audio_b64
        }
        
        await self.ws.send(json.dumps(message))
    
    async def commit_audio(self):
        """Commit the audio buffer (end of candidate's turn)."""
        if not self.ws or not self.connected:
            raise Exception("Not connected to Realtime API")
        
        message = {
            "type": "input_audio_buffer.commit"
        }
        
        await self.ws.send(json.dumps(message))
    
    async def speak_text(self, text: str):
        """
        Make AI speak specific text.
        This is the main method for asking questions.
        """
        if not self.ws or not self.connected:
            raise Exception("Not connected to Realtime API")
        
        # Add message to conversation
        await self.send_text_message(text, role="user")
        
        # Request AI response
        await self.request_response()
        
        print(f"🎤 Requested AI to speak: {text[:50]}...")
    
    async def truncate_response(self):
        """Cancel current AI response."""
        if not self.ws or not self.connected:
            return
        
        message = {
            "type": "response.cancel"
        }
        
        await self.ws.send(json.dumps(message))
    
    async def close(self):
        """Close the WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.connected = False
            print("✅ Realtime API connection closed")