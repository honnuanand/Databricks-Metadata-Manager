# Neon Database Setup for Metadata Manager

## 🚀 Quick Setup Guide

### Step 1: Authenticate with Neon

You need to get a Neon API key:

1. **Go to**: https://console.neon.tech/app/settings/api-keys
2. **Create a new API key**: "metadata-manager-cli"
3. **Copy the key** (it starts with `neon_api_`)
4. **Authenticate the CLI**:
   ```bash
   neonctl auth
   # Paste your API key when prompted
   ```

### Step 2: Create Neon Project

Once authenticated, I can create the database for you, or you can do it manually:

**Option A: Let Claude Code create it**
```bash
# I'll run these commands for you
neonctl projects create --name metadata-manager
neonctl connection-string --project-id <project-id>
```

**Option B: Create via Web Console**
1. Go to: https://console.neon.tech
2. Click "New Project"
3. Name: `metadata-manager`
4. Region: Choose closest to you (us-east-2 recommended)
5. Click "Create Project"
6. Copy the connection string from the dashboard

### Step 3: Get Connection String

The connection string format:
```
postgresql://username:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
```

## 📋 Next Steps (Automated)

Once you provide the connection string, I will:

1. ✅ Add it to Databricks secrets
2. ✅ Update backend configuration
3. ✅ Generate database migrations from SQLAlchemy models
4. ✅ Run migrations to create tables
5. ✅ Test the connection
6. ✅ Deploy to Databricks with persistent storage

## 🔐 Security Notes

- Connection strings will be stored in Databricks secrets (encrypted)
- Never commit connection strings to git
- Use environment variables for local development

## 🎯 Current Status

- [x] Neon CLI installed
- [x] Neon authentication complete
- [x] Database project created
- [x] Connection string obtained
- [x] Migrations generated
- [x] Database initialized
- [x] Deployed to production

## ✅ Setup Complete!

Your Metadata Manager is now running with persistent Neon PostgreSQL storage!

### 📊 Database Details
- **Project**: metadata-manager
- **Project ID**: restless-flower-44746771
- **Region**: aws-us-east-1
- **PostgreSQL Version**: 17
- **Tables Created**: 5 (users, audit_logs, comments, approvals, alembic_version)

### 🔐 Security
- Connection string stored in Databricks secrets: `metadata-manager-secrets/database-url`
- Never commit connection strings to git

### 🌐 Application URL
https://metadata-manager-2409307273843806.aws.databricksapps.com

### 📝 What Changed
1. **Database**: Transitioned from in-memory storage to persistent Neon PostgreSQL
2. **Migrations**: Generated and applied initial schema with all tables
3. **Deployment**: Updated app.yaml to inject DATABASE_URL from Databricks secrets
4. **Testing**: All data will now persist across app restarts and redeployments

### 🧪 Next Steps
1. Test the application by creating users, comments, and approvals
2. Verify data persists after app restart
3. Monitor database usage in Neon console: https://console.neon.tech
4. Set up database backups and branching if needed
