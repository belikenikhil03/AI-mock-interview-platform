"""
Core application configuration using Pydantic settings.
Loads all environment variables and validates them.
"""
from pydantic_settings import BaseSettings
from typing import List
from urllib.parse import quote_plus
from pathlib import Path


def find_env_file() -> str:
    """Find .env file walking up from this file's location."""
    current = Path(__file__).resolve().parent
    for _ in range(4):
        env = current / ".env"
        if env.exists():
            return str(env)
        current = current.parent
    return ".env"


ENV_FILE = find_env_file()
print(f"Loading .env from: {ENV_FILE}")


class Settings(BaseSettings):

    # Application
    APP_NAME: str = "AI Mock Interview Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Azure Credentials
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    AZURE_SUBSCRIPTION_ID: str = ""

    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_STORAGE_CONTAINER_NAME: str = "interview-recordings"

    # Azure SQL Database
    AZURE_SQL_SERVER: str
    AZURE_SQL_DATABASE: str
    AZURE_SQL_USERNAME: str
    AZURE_SQL_PASSWORD: str

    # Azure OpenAI - shared
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-10-01-preview"

    # Azure OpenAI - Chat (resume parsing, question gen, feedback)
    AZURE_OPENAI_CHAT_DEPLOYMENT_NAME: str = "gpt-4o-mini"

    # Azure OpenAI - Realtime (live interview WebSocket)
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4o-realtime-preview"

    # JWT
    JWT_SECRET_KEY: str = "change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Rate Limiting
    MAX_INTERVIEWS_PER_DAY: int = 5
    MAX_INTERVIEW_DURATION_MINUTES: int = 8
    MAX_SILENCE_DURATION_SECONDS: int = 180

    # File Upload
    MAX_RESUME_SIZE_MB: int = 5
    ALLOWED_RESUME_EXTENSIONS: str = ".pdf"

    # Video Storage
    VIDEO_RETENTION_DAYS: int = 30

    @property
    def database_url(self) -> str:
        encoded_password = quote_plus(self.AZURE_SQL_PASSWORD)
        return (
            f"mssql+pyodbc://{self.AZURE_SQL_USERNAME}:{encoded_password}"
            f"@{self.AZURE_SQL_SERVER}/{self.AZURE_SQL_DATABASE}"
            f"?driver=ODBC+Driver+17+for+SQL+Server"
            f"&TrustServerCertificate=yes"
        )

    @property
    def max_resume_size_bytes(self) -> int:
        return self.MAX_RESUME_SIZE_MB * 1024 * 1024

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [ext.strip() for ext in self.ALLOWED_RESUME_EXTENSIONS.split(",")]

    @property
    def chat_api_url(self) -> str:
        """URL for regular chat completions (resume parsing, feedback, questions)."""
        return (
            f"{self.AZURE_OPENAI_ENDPOINT.rstrip('/')}"
            f"/openai/deployments/{self.AZURE_OPENAI_CHAT_DEPLOYMENT_NAME}"
            f"/chat/completions"
            f"?api-version={self.AZURE_OPENAI_API_VERSION}"
        )

    @property
    def realtime_api_url(self) -> str:
        """WebSocket URL for realtime interview sessions."""
        endpoint = self.AZURE_OPENAI_ENDPOINT.rstrip("/")
        endpoint = endpoint.replace("https://", "wss://")
        return (
            f"{endpoint}"
            f"/openai/realtime"
            f"?api-version={self.AZURE_OPENAI_API_VERSION}"
            f"&deployment={self.AZURE_OPENAI_DEPLOYMENT_NAME}"
        )

    model_config = {
        "env_file": ENV_FILE,
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()