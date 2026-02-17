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
