# test_azure_connection.py
from azure.storage.blob import BlobServiceClient
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

# Test SQL Connection
try:
    engine = create_engine(
        f"mssql+pyodbc://{os.getenv('AZURE_SQL_USERNAME')}:{os.getenv('AZURE_SQL_PASSWORD')}"
        f"@{os.getenv('AZURE_SQL_SERVER')}/{os.getenv('AZURE_SQL_DATABASE')}"
        f"?driver=ODBC+Driver+17+for+SQL+Server"
    )
    with engine.connect() as conn:
        print("✅ SQL Database connection successful!")
except Exception as e:
    print(f"❌ SQL connection failed: {e}")

# Test Blob Storage
try:
    blob_service = BlobServiceClient.from_connection_string(
        os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    )
    container = blob_service.get_container_client(os.getenv('AZURE_STORAGE_CONTAINER_NAME'))
    print(f"✅ Blob Storage connection successful!")
except Exception as e:
    print(f"❌ Blob Storage failed: {e}")

print("\n🎉 Azure setup complete!")