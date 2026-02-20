"""
RECOMMENDED FIX: Generate SAS URL for video playback
UPDATE: backend/app/services/storage/storage_service.py
"""
from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions
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
        """Upload resume PDF to blob storage."""
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
        """Upload interview video recording to blob storage."""
        blob_client = self.blob_service.get_blob_client(
            container=self.container_name,
            blob=blob_path
        )
        
        expiry_time = datetime.utcnow() + timedelta(days=settings.VIDEO_RETENTION_DAYS)
        
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

    def get_video_sas_url(self, blob_url: str, expiry_hours: int = 24) -> str:
        """
        Generate a SAS URL for video playback.
        This allows the frontend to access the video without CORS issues.
        
        Args:
            blob_url: The blob URL from database
            expiry_hours: How long the URL should be valid (default 24 hours)
        
        Returns:
            SAS URL that can be used directly in video player
        """
        # Extract blob name from URL
        blob_name = blob_url.split(f"{self.container_name}/")[-1]
        
        # Get account name and key from connection string
        conn_parts = dict(item.split('=', 1) for item in settings.AZURE_STORAGE_CONNECTION_STRING.split(';') if '=' in item)
        account_name = conn_parts.get('AccountName')
        account_key = conn_parts.get('AccountKey')
        
        # Generate SAS token
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
        )
        
        # Return full URL with SAS token
        return f"{blob_url}?{sas_token}"

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