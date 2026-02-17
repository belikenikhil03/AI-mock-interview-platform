"""
Resume service - orchestrates the full resume pipeline:
Upload PDF → Save to Blob → Extract text → Parse with GPT → Save to DB
"""
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status

from app.models.resume import Resume
from app.models.user import User
from app.services.storage.storage_service import StorageService
from app.services.resume.resume_parser import ResumeParserService
from app.core.config import settings


class ResumeService:

    def __init__(self):
        self.storage = StorageService()
        self.parser  = ResumeParserService()

    async def upload_and_parse(
        self,
        db: Session,
        file: UploadFile,
        user: User
    ) -> Resume:
        """
        Full pipeline:
        1. Validate the file
        2. Upload to Azure Blob
        3. Extract text from PDF
        4. Parse with GPT
        5. Save everything to database

        Returns the saved Resume object.
        """

        # ── Step 1: Validate ──────────────────────────────────────────────────
        self._validate_file(file)

        # Read file bytes
        file_bytes = await file.read()

        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty"
            )

        # ── Step 2: Upload to Azure Blob ──────────────────────────────────────
        try:
            blob_result = self.storage.upload_resume(
                file_bytes=file_bytes,
                original_filename=file.filename,
                user_id=user.id
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file to storage: {str(e)}"
            )

        # ── Step 3: Extract text from PDF ─────────────────────────────────────
        try:
            extracted_text = self.parser.extract_text_from_pdf(file_bytes)
        except Exception as e:
            extracted_text = ""
            print(f"PDF text extraction failed: {e}")

        # ── Step 4: Parse with GPT ────────────────────────────────────────────
        parsed_data = {}
        if extracted_text:
            try:
                parsed_data = await self.parser.parse_with_gpt(extracted_text)
            except Exception as e:
                print(f"GPT parsing failed: {e}")
                parsed_data = self.parser._basic_parse(extracted_text)

        # ── Step 5: Save to database ──────────────────────────────────────────
        resume = Resume(
            user_id        = user.id,
            filename       = file.filename,
            blob_url       = blob_result["blob_url"],
            file_size      = blob_result["file_size"],
            extracted_text = extracted_text,
            parsed_data    = parsed_data,
            job_role       = parsed_data.get("job_role"),
            experience_years = parsed_data.get("experience_years"),
            skills         = parsed_data.get("skills", [])
        )

        db.add(resume)
        db.commit()
        db.refresh(resume)

        return resume

    def get_user_resumes(self, db: Session, user_id: int) -> list:
        """Get all resumes for a user, newest first."""
        return (
            db.query(Resume)
            .filter(Resume.user_id == user_id)
            .order_by(Resume.uploaded_at.desc())
            .all()
        )

    def get_resume_by_id(self, db: Session, resume_id: int, user_id: int) -> Resume:
        """Get a specific resume, verifying it belongs to the user."""
        resume = (
            db.query(Resume)
            .filter(Resume.id == resume_id, Resume.user_id == user_id)
            .first()
        )
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        return resume

    def delete_resume(self, db: Session, resume_id: int, user_id: int) -> bool:
        """Delete a resume from DB and Blob storage."""
        resume = self.get_resume_by_id(db, resume_id, user_id)

        # Delete from blob storage
        # Extract blob name from URL
        blob_name = "/".join(resume.blob_url.split("/")[-3:])
        self.storage.delete_blob(blob_name)

        # Delete from database
        db.delete(resume)
        db.commit()
        return True

    def _validate_file(self, file: UploadFile):
        """Validate file type and size."""
        # Check extension
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )

        ext = "." + file.filename.split(".")[-1].lower()
        if ext not in settings.allowed_extensions_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only PDF files are allowed. Got: {ext}"
            )

        # Check content type
        if file.content_type and "pdf" not in file.content_type.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a PDF"
            )
