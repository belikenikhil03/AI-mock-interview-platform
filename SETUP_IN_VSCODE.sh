#!/bin/bash

# =============================================================================
# AI MOCK INTERVIEW PLATFORM - COMPLETE PROJECT SETUP
# =============================================================================
# Run this script in your VS Code project folder where you created venv
# Usage: bash SETUP_IN_VSCODE.sh
# =============================================================================

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║      AI MOCK INTERVIEW PLATFORM - PROJECT SETUP                     ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "This script will create the complete project structure in your current directory."
echo "Current directory: $(pwd)"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled."
    exit 1
fi

echo ""
echo "Creating directory structure..."

# Create all directories
mkdir -p backend/app/{api/{endpoints,schemas,dependencies},core,models,services/{auth,resume,interview,feedback,storage},ml_engine/{analyzers,processors},utils,websocket}
mkdir -p backend/{tests/{unit,integration},migrations}
mkdir -p frontend/src/{components/{auth,dashboard,interview/{setup,active,feedback},common/{ui,layout}},pages,hooks/{useAuth,useInterview,useMediaStream},services/{api,websocket},utils/{mediapipe,validation},context,styles}
mkdir -p frontend/public/assets
mkdir -p {config,scripts/{setup,deployment},docs/{api,architecture},logs}

echo "✓ Directory structure created"
echo ""
echo "Creating backend files..."

# =============================================================================
# BACKEND FILES
# =============================================================================

# requirements.txt
cat > backend/requirements.txt << 'EOFREQ'
# Core Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
websockets==12.0

# Azure Services
azure-identity==1.15.0
azure-storage-blob==12.19.0
azure-ai-openai==1.0.0b1

# Database
pyodbc==5.0.1
sqlalchemy==2.0.25
alembic==1.13.1

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.1.2

# Resume Processing
PyMuPDF==1.23.21
pdfplumber==0.10.4

# ML & Audio/Video Processing
numpy==1.26.3
pandas==2.1.4
scikit-learn==1.4.0
scipy==1.11.4
librosa==0.10.1
soundfile==0.12.1
opencv-python==4.9.0.80

# Utilities
python-dotenv==1.0.0
pydantic==2.5.3
pydantic-settings==2.1.0
httpx==0.26.0
aiofiles==23.2.1

# Development
pytest==7.4.4
pytest-asyncio==0.23.3
black==24.1.1
flake8==7.0.0
EOFREQ

# Core config.py
cat > backend/app/core/config.py << 'EOFCONFIG'
"""Core application configuration using Pydantic settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    APP_NAME: str = "AI Mock Interview Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    AZURE_TENANT_ID: str
    AZURE_CLIENT_ID: str
    AZURE_CLIENT_SECRET: str
    AZURE_SUBSCRIPTION_ID: str
    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_STORAGE_CONTAINER_NAME: str = "interview-recordings"
    AZURE_SQL_SERVER: str
    AZURE_SQL_DATABASE: str
    AZURE_SQL_USERNAME: str
    AZURE_SQL_PASSWORD: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-realtime-mini"
    AZURE_OPENAI_API_VERSION: str = "2024-10-01-preview"
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    MAX_INTERVIEWS_PER_DAY: int = 5
    MAX_INTERVIEW_DURATION_MINUTES: int = 8
    MAX_SILENCE_DURATION_SECONDS: int = 180
    MAX_RESUME_SIZE_MB: int = 5
    ALLOWED_RESUME_EXTENSIONS: list = [".pdf"]
    VIDEO_RETENTION_DAYS: int = 30
    
    @property
    def database_url(self) -> str:
        return (
            f"mssql+pyodbc://{self.AZURE_SQL_USERNAME}:{self.AZURE_SQL_PASSWORD}"
            f"@{self.AZURE_SQL_SERVER}/{self.AZURE_SQL_DATABASE}"
            f"?driver=ODBC+Driver+18+for+SQL+Server"
        )
    
    @property
    def max_resume_size_bytes(self) -> int:
        return self.MAX_RESUME_SIZE_MB * 1024 * 1024
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
EOFCONFIG

# Core database.py
cat > backend/app/core/database.py << 'EOFDB'
"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
EOFDB

# Core security.py
cat > backend/app/core/security.py << 'EOFSEC'
"""Security utilities for JWT and password hashing."""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
EOFSEC

# Core __init__.py
cat > backend/app/core/__init__.py << 'EOFCOREINIT'
from .config import settings
from .database import Base, engine, get_db, SessionLocal
from .security import verify_password, get_password_hash, create_access_token, decode_access_token

__all__ = ["settings", "Base", "engine", "get_db", "SessionLocal", 
           "verify_password", "get_password_hash", "create_access_token", "decode_access_token"]
EOFCOREINIT

# Models user.py
cat > backend/app/models/user.py << 'EOFUSER'
"""User model for authentication."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="user", cascade="all, delete-orphan")
EOFUSER

# Models resume.py
cat > backend/app/models/resume.py << 'EOFRESUME'
"""Resume model for storing uploaded resumes."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    blob_url = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    parsed_data = Column(JSON, nullable=True)
    extracted_text = Column(Text, nullable=True)
    job_role = Column(String(255), nullable=True)
    experience_years = Column(Integer, nullable=True)
    skills = Column(JSON, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="resumes")
    interviews = relationship("Interview", back_populates="resume")
EOFRESUME

# Models interview.py
cat > backend/app/models/interview.py << 'EOFINTERVIEW'
"""Interview session model."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..core.database import Base


class InterviewStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Interview(Base):
    __tablename__ = "interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(SQLEnum(InterviewStatus), default=InterviewStatus.PENDING, nullable=False)
    job_role = Column(String(255), nullable=True)
    interview_type = Column(String(100), nullable=True)
    video_blob_url = Column(String(500), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    questions_asked = Column(JSON, nullable=True)
    responses_given = Column(JSON, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="interviews")
    resume = relationship("Resume", back_populates="interviews")
    feedback = relationship("Feedback", back_populates="interview", uselist=False, cascade="all, delete-orphan")
    metrics = relationship("InterviewMetric", back_populates="interview", cascade="all, delete-orphan")
EOFINTERVIEW

# Models feedback.py
cat > backend/app/models/feedback.py << 'EOFFEEDBACK'
"""Feedback model for interview results."""
from sqlalchemy import Column, Integer, ForeignKey, Float, Text, JSON
from sqlalchemy.orm import relationship
from ..core.database import Base


class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False, unique=True, index=True)
    content_score = Column(Float, nullable=True)
    communication_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    strengths = Column(JSON, nullable=True)
    weaknesses = Column(JSON, nullable=True)
    detailed_feedback = Column(Text, nullable=True)
    improvement_suggestions = Column(JSON, nullable=True)
    what_went_right = Column(JSON, nullable=True)
    what_went_wrong = Column(JSON, nullable=True)
    
    interview = relationship("Interview", back_populates="feedback")
EOFFEEDBACK

# Models metric.py
cat > backend/app/models/metric.py << 'EOFMETRIC'
"""Interview metrics model."""
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class InterviewMetric(Base):
    __tablename__ = "interview_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False, index=True)
    filler_words_count = Column(Integer, default=0)
    total_words_spoken = Column(Integer, default=0)
    average_pause_duration = Column(Float, default=0.0)
    longest_pause_duration = Column(Float, default=0.0)
    speech_rate_wpm = Column(Float, default=0.0)
    eye_contact_percentage = Column(Float, default=0.0)
    fidgeting_count = Column(Integer, default=0)
    posture_score = Column(Float, default=0.0)
    voice_confidence_score = Column(Float, default=0.0)
    voice_stability = Column(Float, default=0.0)
    nervousness_detected = Column(Boolean, default=False)
    relevance_score = Column(Float, default=0.0)
    completeness_score = Column(Float, default=0.0)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    interview = relationship("Interview", back_populates="metrics")
EOFMETRIC

# Models __init__.py
cat > backend/app/models/__init__.py << 'EOFMODELSINIT'
from .user import User
from .resume import Resume
from .interview import Interview, InterviewStatus
from .feedback import Feedback
from .metric import InterviewMetric

__all__ = ["User", "Resume", "Interview", "InterviewStatus", "Feedback", "InterviewMetric"]
EOFMODELSINIT

echo "✓ Models created"

# Schema files
cat > backend/app/api/schemas/user.py << 'EOFSCHEMAUSER'
"""User schemas for API validation."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
EOFSCHEMAUSER

cat > backend/app/api/schemas/resume.py << 'EOFSCHEMARESUME'
"""Resume schemas for API validation."""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ResumeUploadResponse(BaseModel):
    resume_id: int
    filename: str
    blob_url: str
    file_size: int
    job_role: Optional[str] = None
    uploaded_at: datetime
    
    class Config:
        from_attributes = True


class ResumeResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    blob_url: str
    file_size: int
    parsed_data: Optional[Dict[str, Any]] = None
    job_role: Optional[str] = None
    experience_years: Optional[int] = None
    skills: Optional[List[str]] = None
    uploaded_at: datetime
    
    class Config:
        from_attributes = True
EOFSCHEMARESUME

cat > backend/app/api/schemas/interview.py << 'EOFSCHEMAINTERVIEW'
"""Interview schemas for API validation."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from ...models.interview import InterviewStatus


class InterviewCreate(BaseModel):
    resume_id: Optional[int] = None
    job_role: Optional[str] = Field(None, max_length=255)
    interview_type: str = Field("job_role", max_length=100)


class InterviewResponse(BaseModel):
    id: int
    session_id: str
    user_id: int
    resume_id: Optional[int] = None
    status: InterviewStatus
    job_role: Optional[str] = None
    interview_type: Optional[str] = None
    duration_seconds: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class InterviewStartResponse(BaseModel):
    session_id: str
    websocket_url: str
    interview_id: int
EOFSCHEMAINTERVIEW

cat > backend/app/api/schemas/feedback.py << 'EOFSCHEMAFEEDBACK'
"""Feedback schemas for API validation."""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class FeedbackResponse(BaseModel):
    id: int
    interview_id: int
    content_score: Optional[float] = None
    communication_score: Optional[float] = None
    confidence_score: Optional[float] = None
    overall_score: Optional[float] = None
    what_went_right: Optional[List[Dict[str, Any]]] = None
    what_went_wrong: Optional[List[Dict[str, Any]]] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    detailed_feedback: Optional[str] = None
    improvement_suggestions: Optional[List[str]] = None
    
    class Config:
        from_attributes = True
EOFSCHEMAFEEDBACK

cat > backend/app/api/schemas/__init__.py << 'EOFSCHEMASINIT'
from .user import UserBase, UserCreate, UserLogin, UserResponse, Token, TokenData
from .resume import ResumeUploadResponse, ResumeResponse
from .interview import InterviewCreate, InterviewResponse, InterviewStartResponse
from .feedback import FeedbackResponse

__all__ = [
    "UserBase", "UserCreate", "UserLogin", "UserResponse", "Token", "TokenData",
    "ResumeUploadResponse", "ResumeResponse",
    "InterviewCreate", "InterviewResponse", "InterviewStartResponse",
    "FeedbackResponse"
]
EOFSCHEMASINIT

echo "✓ Schemas created"

# Auth service
cat > backend/app/services/auth/auth_service.py << 'EOFAUTHSERVICE'
"""Authentication service."""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import timedelta
from ...models.user import User
from ...api.schemas.user import UserCreate, UserLogin
from ...core.security import get_password_hash, verify_password, create_access_token
from ...core.config import settings


class AuthService:
    @staticmethod
    def register_user(db: Session, user_data: UserCreate) -> User:
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise ValueError("Email already registered")
        
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def authenticate_user(db: Session, login_data: UserLogin) -> Optional[User]:
        user = db.query(User).filter(User.email == login_data.email).first()
        if not user or not verify_password(login_data.password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user
    
    @staticmethod
    def create_user_token(user: User) -> str:
        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        return create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
EOFAUTHSERVICE

cat > backend/app/services/auth/__init__.py << 'EOFAUTHINIT'
from .auth_service import AuthService
__all__ = ["AuthService"]
EOFAUTHINIT

echo "✓ Services created"

# Main app
cat > backend/app/main.py << 'EOFMAIN'
"""Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .core.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered mock interview platform",
    debug=settings.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "AI Mock Interview Platform API", "version": settings.APP_VERSION, "status": "operational"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
EOFMAIN

echo "✓ Main app created"

# =============================================================================
# FRONTEND FILES
# =============================================================================

echo ""
echo "Creating frontend files..."

cat > frontend/package.json << 'EOFPACKAGE'
{
  "name": "ai-interview-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@mediapipe/tasks-vision": "^0.10.8",
    "socket.io-client": "^4.6.1",
    "axios": "^1.6.5",
    "zustand": "^4.5.0",
    "react-webcam": "^7.2.0",
    "recharts": "^2.10.3",
    "lucide-react": "^0.314.0",
    "date-fns": "^3.3.1",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0"
  },
  "devDependencies": {
    "typescript": "^5.3.3",
    "@types/node": "^20.11.5",
    "@types/react": "^18.2.48",
    "@types/react-dom": "^18.2.18",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.33",
    "tailwindcss": "^3.4.1",
    "eslint": "^8.56.0",
    "eslint-config-next": "14.1.0"
  }
}
EOFPACKAGE

echo "✓ Frontend package.json created"

# =============================================================================
# CONFIGURATION FILES
# =============================================================================

echo ""
echo "Creating configuration files..."

cat > .env.example << 'EOFENV'
# Azure Configuration
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
AZURE_SUBSCRIPTION_ID=your_subscription_id

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=your_storage_connection_string
AZURE_STORAGE_CONTAINER_NAME=interview-recordings

# Azure SQL Database
AZURE_SQL_SERVER=your_server.database.windows.net
AZURE_SQL_DATABASE=ai_interview_db
AZURE_SQL_USERNAME=your_username
AZURE_SQL_PASSWORD=your_password

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-realtime-mini
AZURE_OPENAI_API_VERSION=2024-10-01-preview

# JWT Authentication
JWT_SECRET_KEY=your_super_secret_key_change_this_in_production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Settings
APP_NAME=AI Mock Interview Platform
APP_VERSION=1.0.0
DEBUG=True
ENVIRONMENT=development

# Rate Limiting
MAX_INTERVIEWS_PER_DAY=5
MAX_INTERVIEW_DURATION_MINUTES=8
MAX_SILENCE_DURATION_SECONDS=180

# File Upload
MAX_RESUME_SIZE_MB=5
ALLOWED_RESUME_EXTENSIONS=.pdf

# Video Storage
VIDEO_RETENTION_DAYS=30
EOFENV

cat > .gitignore << 'EOFGITIGNORE'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
build/
*.egg-info/

# Environment
.env
.env.local

# IDEs
.vscode/
.idea/
*.swp
.DS_Store

# Logs
logs/
*.log

# Database
*.db
*.sqlite

# Node
node_modules/
.next/
out/
.cache/

# Testing
.pytest_cache/
.coverage

# Temporary
*.tmp
*.bak

# Azure
.azure/

# Recordings
recordings/
uploads/
EOFGITIGNORE

echo "✓ Configuration files created"

# =============================================================================
# DOCUMENTATION
# =============================================================================

echo ""
echo "Creating documentation..."

cat > README.md << 'EOFREADME'
# AI Mock Interview Platform

AI-powered mock interview platform with real-time feedback.

## Quick Start

### Backend Setup

1. Activate your virtual environment (if not already activated)
2. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your Azure credentials
```

4. Run backend:
```bash
cd backend/app
uvicorn main:app --reload
```

Backend runs at: http://localhost:8000

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Configure environment:
```bash
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

3. Run frontend:
```bash
npm run dev
```

Frontend runs at: http://localhost:3000

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/schemas/      # Pydantic validation schemas
│   │   ├── core/             # Config, database, security
│   │   ├── models/           # SQLAlchemy models
│   │   ├── services/         # Business logic
│   │   └── main.py           # FastAPI app
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── hooks/            # Custom hooks
│   │   └── services/         # API clients
│   └── package.json
└── .env.example              # Environment template
```

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Azure Services
- **Frontend**: Next.js, React, Tailwind CSS, MediaPipe
- **Database**: Azure SQL Database
- **Storage**: Azure Blob Storage
- **AI**: Azure OpenAI Realtime API

## Database Models

- **User** - Authentication and profile
- **Resume** - Uploaded resumes with parsed data
- **Interview** - Session management
- **Feedback** - Scores and analysis
- **InterviewMetric** - Real-time performance metrics

## Next Steps

1. Configure Azure credentials in `.env`
2. Start building API endpoints in `backend/app/api/endpoints/`
3. Implement service layer methods
4. Create frontend components
5. Integrate WebSocket for real-time communication
EOFREADME

cat > PROJECT_STATUS.md << 'EOFSTATUS'
# Project Status

## ✅ Completed

- [x] Project structure created
- [x] Database models (User, Resume, Interview, Feedback, Metric)
- [x] API schemas (Pydantic validation)
- [x] Core configuration (settings, database, security)
- [x] Authentication service
- [x] Main FastAPI app
- [x] Frontend package configuration

## 📋 Next Steps

### Backend
1. Create API endpoints:
   - Auth endpoints (register, login)
   - Resume endpoints (upload, list)
   - Interview endpoints (create, start, complete)
   - Feedback endpoints (get results)

2. Implement services:
   - Resume parsing service
   - Azure Blob storage service
   - Interview management service
   - Feedback generation service

3. Add WebSocket handler for real-time communication

4. Implement ML analyzers:
   - Audio analysis (filler words, pauses)
   - Video analysis integration
   - Metrics calculation

### Frontend
1. Create authentication pages
2. Build dashboard
3. Implement interview flow
4. Add MediaPipe integration
5. Create feedback display

## 📁 File Count
- Backend Python files: 14
- Configuration files: 3
- Documentation: 2
- Total: 19 files created
EOFSTATUS

echo "✓ Documentation created"

# =============================================================================
# FINISH
# =============================================================================

echo ""
echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║                     SETUP COMPLETE! 🎉                               ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Created:"
echo "   ✓ Complete directory structure"
echo "   ✓ 14 backend Python files"
echo "   ✓ Database models (5 models)"
echo "   ✓ API schemas (4 modules)"
echo "   ✓ Core configuration"
echo "   ✓ Authentication service"
echo "   ✓ Frontend package.json"
echo "   ✓ Documentation (README + STATUS)"
echo ""
echo "🚀 Next Steps:"
echo ""
echo "1. Activate your virtual environment (if not already):"
echo "   source venv/bin/activate"
echo ""
echo "2. Install backend dependencies:"
echo "   cd backend"
echo "   pip install -r requirements.txt"
echo ""
echo "3. Configure your .env file:"
echo "   cp .env.example .env"
echo "   # Edit .env with your Azure credentials"
echo ""
echo "4. Start backend server:"
echo "   cd backend/app"
echo "   uvicorn main:app --reload"
echo ""
echo "5. In another terminal, install frontend dependencies:"
echo "   cd frontend"
echo "   npm install"
echo ""
echo "6. Start frontend:"
echo "   npm run dev"
echo ""
echo "📚 Check README.md for detailed documentation"
echo "📋 Check PROJECT_STATUS.md for development roadmap"
echo ""
echo "Happy coding! 🚀"
