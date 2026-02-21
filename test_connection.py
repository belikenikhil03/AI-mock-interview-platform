"""
Test if your Realtime API credentials actually work.
CREATE: backend/test_realtime_connection.py
RUN: python test_realtime_connection.py
"""
import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

async def test_connection():
    # Build URL
    base_url = ENDPOINT.rstrip("/").replace("https://", "wss://")
    url = f"{base_url}/openai/realtime?api-version=2024-10-01-preview&deployment={DEPLOYMENT}"
    
    print(f"🔗 Testing connection to: {url[:60]}...")
    print(f"🎯 Deployment: {DEPLOYMENT}")
    
    try:
        ws = await websockets.connect(
            url,
            extra_headers={
                "api-key": API_KEY,
                "Content-Type": "application/json"
            },
            ping_interval=20,
            ping_timeout=10
        )
        
        print("✅ WebSocket connected!")
        
        # Configure session
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "voice": "alloy"
            }
        }
        
        await ws.send(json.dumps(config))
        print("📤 Sent session config")
        
        # Wait for session.created
        response = await asyncio.wait_for(ws.recv(), timeout=5)
        data = json.loads(response)
        print(f"📥 Received: {data.get('type')}")
        
        if data.get('type') == 'session.created':
            print("✅ SUCCESS! Realtime API is working!")
            print(f"Session ID: {data.get('session', {}).get('id')}")
            
            # Test speaking
            speak_msg = {
                "type": "response.create",
                "response": {
                    "modalities": ["audio", "text"],
                    "instructions": "Say 'Hello, this is a test'"
                }
            }
            
            await ws.send(json.dumps(speak_msg))
            print("📤 Requested speech...")
            
            # Listen for audio
            audio_received = False
            for _ in range(10):  # Wait max 10 messages
                msg = await asyncio.wait_for(ws.recv(), timeout=3)
                msg_data = json.loads(msg)
                print(f"   Received: {msg_data.get('type')}")
                
                if msg_data.get('type') == 'response.audio.delta':
                    audio_received = True
                    print("✅ AUDIO RECEIVED! Realtime API is fully working!")
                    break
            
            if not audio_received:
                print("⚠️  Connected but no audio received")
        
        else:
            print(f"⚠️  Unexpected response: {data}")
        
        await ws.close()
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        print("\nCheck:")
        print("1. AZURE_OPENAI_ENDPOINT is correct")
        print("2. AZURE_OPENAI_API_KEY is valid")
        print("3. AZURE_OPENAI_DEPLOYMENT_NAME = 'gpt-realtime-mini'")
        print("4. Deployment exists in your Azure Portal")

if __name__ == "__main__":
    asyncio.run(test_connection())