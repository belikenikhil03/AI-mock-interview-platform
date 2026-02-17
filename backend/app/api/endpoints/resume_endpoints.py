"""
Resume API endpoints.
Handles PDF upload, listing, and retrieval.
"""
from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.dependencies.deps import get_current_user
from app.api.schemas.resume import ResumeResponse, ResumeUploadResponse
from app.services.resume.resume_service import ResumeService
from app.models.user import User

router = APIRouter()


@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a resume PDF"
)
async def upload_resume(
    file: UploadFile = File(..., description="PDF resume file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a resume PDF. Pipeline:
    1. Validates the file (PDF only, max 5MB)
    2. Uploads to Azure Blob Storage
    3. Extracts text from PDF
    4. Parses with GPT (job role, skills, experience)
    5. Saves to database

    Returns the resume with parsed data.
    """
    service = ResumeService()
    resume = await service.upload_and_parse(db, file, current_user)

    return {
        "resume_id":   resume.id,
        "filename":    resume.filename,
        "blob_url":    resume.blob_url,
        "file_size":   resume.file_size,
        "job_role":    resume.job_role,
        "skills":      resume.skills or [],
        "experience_years": resume.experience_years,
        "parsed_data": resume.parsed_data,
        "uploaded_at": resume.uploaded_at
    }


@router.get(
    "/",
    response_model=List[ResumeResponse],
    summary="List all resumes for current user"
)
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all uploaded resumes for the logged-in user."""
    service = ResumeService()
    return service.get_user_resumes(db, current_user.id)


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    summary="Get a specific resume"
)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get details of a specific resume by ID."""
    service = ResumeService()
    return service.get_resume_by_id(db, resume_id, current_user.id)


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a resume"
)
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a resume from database and Azure Blob Storage."""
    service = ResumeService()
    service.delete_resume(db, resume_id, current_user.id)
