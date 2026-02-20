"""
Azure Speech token endpoint.
CREATE: backend/app/api/endpoints/speech.py
"""
from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies.deps import get_current_user
from app.models.user import User
from app.core.config import settings
import requests

router = APIRouter()


@router.get("/token")
async def get_speech_token(current_user: User = Depends(get_current_user)):
    """
    Get Azure Speech Services token for frontend.
    Token is valid for 10 minutes.
    """
    try:
        # Azure Speech token endpoint
        token_url = f"https://{settings.AZURE_SPEECH_REGION}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        
        headers = {
            "Ocp-Apim-Subscription-Key": settings.AZURE_SPEECH_KEY
        }
        
        response = requests.post(token_url, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to get speech token")
        
        token = response.text
        
        return {
            "token": token,
            "region": settings.AZURE_SPEECH_REGION
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))