"""
Azure OpenAI Realtime API Client.
backend/app/services/realtime/realtime_client.py
"""
import asyncio
import json
import websockets
from typing import Callable, Optional

from app.core.config import settings


class RealtimeAPIClient:
    
    def __init__(self):
        self.ws = None
        self.on_audio_callback: Optional[Callable] = None
        self.on_done_callback: Optional[Callable] = None
        self.connected = False
        
    async def connect(self):
        """Connect to Azure OpenAI Realtime API WebSocket."""
        # Build WebSocket URL
        endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/").replace("https://", "wss://")
        url = f"{endpoint}/openai/realtime?api-version={settings.AZURE_OPENAI_API_VERSION}&deployment={settings.AZURE_OPENAI_DEPLOYMENT_NAME}"
        
        headers = {
            "api-key": settings.AZURE_OPENAI_API_KEY
        }
        
        try:
            self.ws = await websockets.connect(url, extra_headers=headers)
            self.connected = True
            print("✅ Connected to Azure Realtime API")
            
            # Start listening for responses
            asyncio.create_task(self._listen())
            
        except Exception as e:
            print(f"❌ Realtime API connection failed: {e}")
            raise
    
    async def _listen(self):
        """Listen for audio/text responses from Azure."""
        try:
            async for message in self.ws:
                data = json.loads(message)
                
                msg_type = data.get("type", "")
                
                # Audio chunk received
                if msg_type == "response.audio.delta":
                    audio_b64 = data.get("delta", "")
                    if self.on_audio_callback and audio_b64:
                        await self.on_audio_callback(audio_b64)
                
                # Response complete
                elif msg_type == "response.done":
                    if self.on_done_callback:
                        await self.on_done_callback()
                        
        except websockets.exceptions.ConnectionClosed:
            print("Realtime API connection closed")
            self.connected = False
        except Exception as e:
            print(f"Realtime API listen error: {e}")
            self.connected = False
    
    async def speak_text(self, text: str):
        """
        Make AI speak text aloud.
        
        Args:
            text: What the AI should say
        """
        if not self.ws or not self.connected:
            raise Exception("Not connected to Realtime API")
        
        message = {
            "type": "response.create",
            "response": {
                "modalities": ["audio", "text"],
                "instructions": f"You are a professional job interviewer with a warm, clear voice. Say this naturally: {text}",
                "voice": "alloy"  # Professional male voice
            }
        }
        
        await self.ws.send(json.dumps(message))
        print(f"🎤 AI speaking: {text[:50]}...")
    
    async def close(self):
        """Close the WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.connected = False
            print("✅ Realtime API connection closed")