# Azure Portal Setup Guide - AI Mock Interview Platform

This guide will walk you through setting up all required Azure services for the project.

## 📋 What We Need to Create

1. **Resource Group** - Container for all resources
2. **Azure SQL Database** - Store user data, interviews, feedback
3. **Azure Blob Storage** - Store resumes and video recordings
4. **Azure OpenAI** - AI interview conversations
5. **Azure AD B2C (Optional)** - Advanced authentication (can use JWT first)

---

## 🚀 Step-by-Step Setup

### Step 1: Create Resource Group

A resource group keeps all your resources organized in one place.

1. **Login to Azure Portal**: https://portal.azure.com
2. Click **"Resource groups"** in the left menu (or search for it)
3. Click **"+ Create"**
4. Fill in:
   - **Subscription**: Select your subscription (likely "Azure for Students" or "Free Trial")
   - **Resource group name**: `ai-interview-rg`
   - **Region**: Choose closest to you (e.g., `East US`, `West Europe`, `Southeast Asia`)
5. Click **"Review + Create"** → **"Create"**

✅ **You now have a container for all resources!**

---

### Step 2: Create Azure SQL Database

This will store all your application data (users, interviews, feedback, metrics).

1. **Search for "SQL databases"** in the top search bar
2. Click **"+ Create"**

#### Basic Settings:
- **Subscription**: Your subscription
- **Resource group**: Select `ai-interview-rg` (the one you just created)
- **Database name**: `ai-interview-db`
- **Server**: Click **"Create new"**

#### Create SQL Server (popup):
- **Server name**: `ai-interview-server-[yourname]` (must be globally unique)
  - Example: `ai-interview-server-john123`
- **Location**: Same as your resource group
- **Authentication method**: Select **"Use SQL authentication"**
- **Server admin login**: `sqladmin` (or any username you want)
- **Password**: Create a strong password (save this!)
  - Example: `MySecurePass123!`
- Click **"OK"**

#### Back to Database Settings:
- **Want to use SQL elastic pool?**: No
- **Compute + storage**: Click **"Configure database"**
  - Select **"Basic"** (cheapest option - 2GB, ~$5/month)
  - Or select **"DTU-based"** → **"Basic"** → **Apply**

#### Backup Storage Redundancy:
- Select **"Locally-redundant backup storage"** (cheapest)

3. Click **"Review + Create"** → **"Create"**
4. **Wait 3-5 minutes** for deployment

#### After Creation - Get Connection Details:

1. Go to your SQL Database (`ai-interview-db`)
2. Click **"Connection strings"** in the left menu
3. Copy the **ADO.NET** connection string - it looks like:
```
Server=tcp:ai-interview-server-john123.database.windows.net,1433;Initial Catalog=ai-interview-db;Persist Security Info=False;User ID=sqladmin;Password={your_password};MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;
```

4. **IMPORTANT - Configure Firewall**:
   - In your SQL Server (not database), click **"Networking"** in left menu
   - Under **"Firewall rules"**:
     - Click **"Add your client IPv4 address"** (this allows your computer)
     - Toggle **"Allow Azure services and resources to access this server"** to **ON**
   - Click **"Save"**

✅ **Save these for .env file:**
```
AZURE_SQL_SERVER=ai-interview-server-john123.database.windows.net
AZURE_SQL_DATABASE=ai-interview-db
AZURE_SQL_USERNAME=sqladmin
AZURE_SQL_PASSWORD=MySecurePass123!
```

---

### Step 3: Create Azure Storage Account (for Blob Storage)

This stores resume PDFs and video recordings.

1. **Search for "Storage accounts"** in the top search bar
2. Click **"+ Create"**

#### Basics:
- **Subscription**: Your subscription
- **Resource group**: `ai-interview-rg`
- **Storage account name**: `aiinterviewstorage[yourname]` (must be lowercase, no hyphens, globally unique)
  - Example: `aiinterviewstoragejohn`
- **Region**: Same as before
- **Performance**: **Standard**
- **Redundancy**: **Locally-redundant storage (LRS)** (cheapest)

3. Click **"Review"** → **"Create"**
4. **Wait 1-2 minutes** for deployment

#### After Creation - Get Connection String:

1. Go to your storage account
2. Click **"Access keys"** in the left menu under "Security + networking"
3. Under **"key1"**, click **"Show"** next to **"Connection string"**
4. Click **"Copy to clipboard"**

It looks like:
```
DefaultEndpointsProtocol=https;AccountName=aiinterviewstoragejohn;AccountKey=ABC123...;EndpointSuffix=core.windows.net
```

#### Create Blob Container:

1. In your storage account, click **"Containers"** in the left menu (under "Data storage")
2. Click **"+ Container"**
3. Name: `interview-recordings`
4. Public access level: **Private (no anonymous access)**
5. Click **"Create"**

✅ **Save for .env file:**
```
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=aiinterviewstoragejohn;AccountKey=ABC123...
AZURE_STORAGE_CONTAINER_NAME=interview-recordings
```

---

### Step 4: Create Azure OpenAI Resource

This powers the AI interviewer.

1. **Search for "Azure OpenAI"** in the top search bar
2. Click **"+ Create"**

#### Basics:
- **Subscription**: Your subscription
- **Resource group**: `ai-interview-rg`
- **Region**: **IMPORTANT - Choose a region that supports Realtime API**
  - Recommended: `Sweden Central` or `East US 2`
  - Check availability: https://learn.microsoft.com/azure/ai-services/openai/concepts/models
- **Name**: `ai-interview-openai-[yourname]`
  - Example: `ai-interview-openai-john`
- **Pricing tier**: **Standard S0**

3. Click **"Review + submit"** → **"Create"**
4. **Wait 2-3 minutes**

#### After Creation - Get Keys:

1. Go to your OpenAI resource
2. Click **"Keys and Endpoint"** in the left menu
3. You'll see:
   - **Endpoint**: `https://ai-interview-openai-john.openai.azure.com/`
   - **KEY 1**: Click "Show" and copy it

#### Deploy the Model:

1. Click **"Model deployments"** in the left menu (or go to Azure OpenAI Studio)
2. Click **"Create new deployment"** or **"Manage Deployments"** → **"Create"**
3. Fill in:
   - **Select a model**: Choose **`gpt-4o-realtime-preview`** (if available)
     - If not available, use **`gpt-4o`** for now (you may need to request access)
   - **Deployment name**: `gpt-realtime-mini` (or `gpt-4o-deployment`)
   - **Model version**: Latest available
4. Click **"Create"**

**Note**: Realtime API might require申请 access. If not available:
- Start with `gpt-4o` or `gpt-4-turbo` for development
- Request Realtime API access through Azure support

✅ **Save for .env file:**
```
AZURE_OPENAI_ENDPOINT=https://ai-interview-openai-john.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-realtime-mini
AZURE_OPENAI_API_VERSION=2024-10-01-preview
```

---

### Step 5: Get Azure Credentials (for SDK authentication)

For programmatic access to Azure services.

1. **Search for "Azure Active Directory"** (or "Microsoft Entra ID")
2. Click **"App registrations"** in the left menu
3. Click **"+ New registration"**
4. Fill in:
   - **Name**: `ai-interview-app`
   - **Supported account types**: **Accounts in this organizational directory only**
   - **Redirect URI**: Leave blank
5. Click **"Register"**

#### Get Application Credentials:

1. After creation, you'll see the **Overview** page
2. **Copy these values**:
   - **Application (client) ID**: This is your `AZURE_CLIENT_ID`
   - **Directory (tenant) ID**: This is your `AZURE_TENANT_ID`

3. Click **"Certificates & secrets"** in the left menu
4. Click **"+ New client secret"**
5. Description: `ai-interview-secret`
6. Expires: Choose **24 months** (or custom)
7. Click **"Add"**
8. **IMMEDIATELY COPY THE VALUE** (you can't see it again!)
   - This is your `AZURE_CLIENT_SECRET`

#### Get Subscription ID:

1. Search for **"Subscriptions"** in the top search bar
2. Click on your subscription name
3. Copy the **Subscription ID**

✅ **Save for .env file:**
```
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret-value
AZURE_SUBSCRIPTION_ID=your-subscription-id
```

---

## 📝 Complete .env File

Now create your `.env` file with all the values:

```env
# Azure Credentials
AZURE_TENANT_ID=your-tenant-id-from-step5
AZURE_CLIENT_ID=your-client-id-from-step5
AZURE_CLIENT_SECRET=your-client-secret-from-step5
AZURE_SUBSCRIPTION_ID=your-subscription-id-from-step5

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=aiinterviewstoragejohn;AccountKey=...
AZURE_STORAGE_CONTAINER_NAME=interview-recordings

# Azure SQL Database
AZURE_SQL_SERVER=ai-interview-server-john123.database.windows.net
AZURE_SQL_DATABASE=ai-interview-db
AZURE_SQL_USERNAME=sqladmin
AZURE_SQL_PASSWORD=MySecurePass123!

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://ai-interview-openai-john.openai.azure.com/
AZURE_OPENAI_API_KEY=your-openai-key-from-step4
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-realtime-mini
AZURE_OPENAI_API_VERSION=2024-10-01-preview

# JWT Authentication (generate a random secret)
JWT_SECRET_KEY=your-super-secret-random-string-change-this
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
```

---

## 💰 Cost Breakdown (Approximate Monthly)

With $1000 Azure credits:

| Service | Configuration | Est. Monthly Cost | Usage |
|---------|--------------|-------------------|-------|
| **SQL Database** | Basic (2GB) | ~$5 | Always on |
| **Blob Storage** | LRS | ~$1-2 | Per GB stored |
| **Azure OpenAI** | Pay-per-use | ~$1-2 per interview | 465-533 interviews |
| **Data Transfer** | Minimal | ~$1 | Minimal usage |
| **Total (excluding OpenAI)** | | ~$7-9/month | Fixed costs |
| **OpenAI (variable)** | | ~$1.50 per 8-min interview | 465-533 total interviews |

**Total Budget Usage**: ~$700-800 for MVP (allows 465-533 interviews)

---

## ✅ Verification Checklist

- [ ] Resource group created (`ai-interview-rg`)
- [ ] SQL Database created and firewall configured
- [ ] Storage account created with container
- [ ] Azure OpenAI resource created with model deployed
- [ ] App registration created with client secret
- [ ] All credentials copied to `.env` file
- [ ] Firewall rules allow your IP address
- [ ] Connection strings tested

---

## 🧪 Test Your Setup

After setting up `.env`, test the connection:

```python
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
        f"?driver=ODBC+Driver+18+for+SQL+Server"
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
```

---

## 🆘 Troubleshooting

### "Cannot connect to SQL Database"
- Check firewall rules in Azure Portal
- Verify username/password are correct
- Ensure "Allow Azure services" is enabled

### "Storage account not found"
- Verify connection string is complete (very long string)
- Check storage account name matches exactly

### "OpenAI model not available"
- Some models require申请 access
- Try `gpt-4o` or `gpt-4-turbo` instead
- Check region availability

### "Insufficient quota"
- Request quota increase in Azure Portal
- Start with smaller models for testing

---

## 📚 Next Steps

Once Azure is set up:
1. ✅ Run the `SETUP_IN_VSCODE.sh` script
2. ✅ Copy all values to `.env` file
3. ✅ Install backend dependencies: `pip install -r backend/requirements.txt`
4. ✅ Test connections with script above
5. ✅ Start building! Backend: `uvicorn main:app --reload`

---

**Need help?** Each Azure service has a "Help" button in the portal with documentation and support options.
