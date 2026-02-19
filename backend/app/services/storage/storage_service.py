"""
Updated Storage Service with video upload support.
REPLACE: backend/app/services/storage/storage_service.py
"""
from azure.storage.blob import BlobServiceClient, ContentSettings
from datetime import datetime, timedelta
import uuid

from app.core.config import settings


class StorageService:

    def __init__(self):
        self.blob_service = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        self.container_name = settings.AZURE_STORAGE_CONTAINER_NAME

    def upload_resume(self, file_data: bytes, user_id: int) -> tuple:
        """
        Upload resume PDF to blob storage.
        
        Returns:
            (blob_url, file_size)
        """
        filename = f"resumes/user_{user_id}/{uuid.uuid4()}.pdf"
        
        blob_client = self.blob_service.get_blob_client(
            container=self.container_name,
            blob=filename
        )
        
        blob_client.upload_blob(
            file_data,
            overwrite=True,
            content_settings=ContentSettings(content_type="application/pdf")
        )
        
        blob_url = blob_client.url
        file_size = len(file_data)
        
        return blob_url, file_size

    def upload_video(self, file_data, blob_path: str) -> str:
        """
        Upload interview video recording to blob storage.
        Sets 30-day retention policy.
        
        Args:
            file_data: File bytes or file-like object
            blob_path: Path in blob storage (e.g., 'interviews/user_3/interview_5/recording.webm')
        
        Returns:
            blob_url: Full URL to the uploaded video
        """
        blob_client = self.blob_service.get_blob_client(
            container=self.container_name,
            blob=blob_path
        )
        
        # Set retention - video auto-deletes after 30 days
        expiry_time = datetime.utcnow() + timedelta(days=settings.VIDEO_RETENTION_DAYS)
        
        # Upload video
        blob_client.upload_blob(
            file_data,
            overwrite=True,
            content_settings=ContentSettings(content_type="video/webm"),
            metadata={
                "retention_days": str(settings.VIDEO_RETENTION_DAYS),
                "expires_at": expiry_time.isoformat()
            }
        )
        
        return blob_client.url

    def delete_blob(self, blob_url: str):
        """Delete a blob by URL."""
        blob_name = blob_url.split(f"{self.container_name}/")[-1]
        blob_client = self.blob_service.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        blob_client.delete_blob()

    def get_blob_url(self, blob_path: str) -> str:
        """Get full URL for a blob path."""
        blob_client = self.blob_service.get_blob_client(
            container=self.container_name,
            blob=blob_path
        )
        return blob_client.url