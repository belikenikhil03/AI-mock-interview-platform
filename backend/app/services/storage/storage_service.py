"""
Azure Blob Storage service.
Handles all file upload/download/delete operations.
"""
from azure.storage.blob import BlobServiceClient, ContentSettings
from datetime import datetime, timedelta
import uuid
import os

from app.core.config import settings


class StorageService:

    def __init__(self):
        self.client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        self.container = settings.AZURE_STORAGE_CONTAINER_NAME

    def upload_resume(self, file_bytes: bytes, original_filename: str, user_id: int) -> dict:
        """
        Upload a resume PDF to Azure Blob Storage.

        Returns:
            dict with blob_url, blob_name, file_size
        """
        # Generate unique blob name: resumes/user_1/uuid_filename.pdf
        ext = os.path.splitext(original_filename)[1].lower()
        blob_name = f"resumes/user_{user_id}/{uuid.uuid4().hex}{ext}"

        blob_client = self.client.get_blob_client(
            container=self.container,
            blob=blob_name
        )

        blob_client.upload_blob(
            file_bytes,
            overwrite=True,
            content_settings=ContentSettings(content_type="application/pdf")
        )

        return {
            "blob_name": blob_name,
            "blob_url": blob_client.url,
            "file_size": len(file_bytes)
        }

    def upload_video(self, file_bytes: bytes, session_id: str) -> dict:
        """
        Upload an interview recording to Azure Blob Storage.
        Sets a TTL tag for automatic deletion after VIDEO_RETENTION_DAYS.

        Returns:
            dict with blob_url, blob_name, file_size
        """
        blob_name = f"recordings/{session_id}/{uuid.uuid4().hex}.webm"

        blob_client = self.client.get_blob_client(
            container=self.container,
            blob=blob_name
        )

        # Tag with expiry date for lifecycle management
        expiry_date = (
            datetime.utcnow() + timedelta(days=settings.VIDEO_RETENTION_DAYS)
        ).strftime("%Y-%m-%d")

        blob_client.upload_blob(
            file_bytes,
            overwrite=True,
            content_settings=ContentSettings(content_type="video/webm"),
            tags={"expiry_date": expiry_date}
        )

        return {
            "blob_name": blob_name,
            "blob_url": blob_client.url,
            "file_size": len(file_bytes)
        }

    def delete_blob(self, blob_name: str) -> bool:
        """Delete a blob by name. Returns True if deleted."""
        try:
            blob_client = self.client.get_blob_client(
                container=self.container,
                blob=blob_name
            )
            blob_client.delete_blob()
            return True
        except Exception:
            return False

    def get_blob_url(self, blob_name: str) -> str:
        """Get the public URL for a blob."""
        blob_client = self.client.get_blob_client(
            container=self.container,
            blob=blob_name
        )
        return blob_client.url
