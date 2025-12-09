# Metadata Manager - Databricks Deployment Guide

## Prerequisites

1. **Databricks CLI** installed and configured
2. **Databricks Personal Access Token** (PAT) for the app
3. **Node.js 18+** for building frontend
4. **Python 3.11+** for backend

## Secret Scope Setup

A secret scope named `metadata-manager-secrets` should be created with the following secrets:

| Secret Key | Description | Required |
|------------|-------------|----------|
| `databricks-host` | Workspace URL | ✅ Yes |
| `databricks-token` | PAT for Unity Catalog API access | ✅ Yes |
| `database-url` | PostgreSQL connection string (Neon) | ✅ Yes |
| `secret-key` | JWT signing key | ✅ Yes |

## Setting Up Secrets

### 1. Create Secret Scope

```bash
# Create the secret scope (if it doesn't exist)
databricks secrets create-scope metadata-manager-secrets
```

### 2. Add Databricks Token

Generate a Personal Access Token (PAT):

1. Go to your Databricks workspace
2. Click on your user icon (top right) → Settings
3. Click on "Developer" → "Access tokens"
4. Click "Generate new token"
5. Give it a name: `metadata-manager-app`
6. Set expiration: 90 days recommended
7. Click "Generate"
8. **Copy the token immediately**

Add to secret scope:

```bash
databricks secrets put-secret metadata-manager-secrets databricks-token --string-value "dapi..."
databricks secrets put-secret metadata-manager-secrets databricks-host --string-value "https://your-workspace.cloud.databricks.com"
```

### 3. Add Database Connection String

See [NEON_SETUP.md](NEON_SETUP.md) for setting up the PostgreSQL database.

```bash
databricks secrets put-secret metadata-manager-secrets database-url --string-value "postgresql://user:pass@host/db?sslmode=require"
```

### 4. Add JWT Secret Key

```bash
# Generate a secure random key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to secrets
databricks secrets put-secret metadata-manager-secrets secret-key --string-value "your-generated-key"
```

## Verify Secrets

```bash
# List all secrets in the scope
databricks secrets list-secrets metadata-manager-secrets
```

## Deploy the Application

### One-Command Deployment

The deployment script handles everything automatically:

```bash
# From the project root directory
python deploy_to_databricks.py
```

The script will:
1. ✅ Build the React frontend (`npm run build`)
2. ✅ Copy static files to backend/static
3. ✅ Package the backend code
4. ✅ Upload to Databricks workspace
5. ✅ Create/update Databricks App with secrets

### Deployment Options

```bash
# Regular deployment (creates or updates app)
python deploy_to_databricks.py

# Hard redeploy (delete and recreate app)
python deploy_to_databricks.py --hard-redeploy

# Custom workspace path
python deploy_to_databricks.py --workspace-path /Workspace/Users/your-email@domain.com/metadata-manager
```

### What Gets Deployed

**Backend:**
- FastAPI application
- SQLAlchemy models and migrations
- Databricks Unity Catalog integration
- Authentication and authorization logic

**Frontend:**
- React application (built and served as static files)
- Material-UI components
- Redux state management
- In-app test runner

**Configuration:**
All secrets are injected from Databricks secrets scope:
- `DATABRICKS_HOST`: Workspace URL
- `DATABRICKS_TOKEN`: Unity Catalog API access
- `DATABASE_URL`: PostgreSQL connection
- `SECRET_KEY`: JWT signing key

## Post-Deployment

### Access the Application

After successful deployment:

1. The deployment script will output the app URL
2. Or navigate to: Workspace → Apps → metadata-manager
3. Click to open the application

**Example URL:**
```
https://metadata-manager-{app-id}.{region}.databricksapps.com
```

### Initial Setup

1. **Initialize Databricks Schema:**
   ```bash
   export DATABRICKS_TOKEN="your-token"
   export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
   python databricks/create_schema_sql.py
   ```

2. **Login with Test User:**
   - Email: `admin@example.com`
   - Password: `admin123`

3. **Verify Functionality:**
   - Browse catalogs
   - Create test comment suggestion
   - Run in-app tests at `/test-runner`

## Troubleshooting

### Secrets Not Found

```bash
# List available scopes
databricks secrets list-scopes

# List secrets in scope
databricks secrets list-secrets metadata-manager-secrets

# Get specific secret (returns metadata only, not value)
databricks secrets get-secret metadata-manager-secrets database-url
```

### Deployment Fails

```bash
# Check if app exists
databricks apps list

# Get app details and status
databricks apps get metadata-manager

# Delete and redeploy
python deploy_to_databricks.py --hard-redeploy
```

### Frontend Build Fails

```bash
# Install dependencies
cd front-end
npm install

# Build manually
npm run build

# Check for build errors
ls -la dist/
```

### App Returns 502 Error

Common causes:
1. Backend startup error (check logs)
2. Missing environment variables (check secrets)
3. Database connection failure (verify DATABASE_URL)

```bash
# View app logs
databricks apps logs metadata-manager

# Check app events
databricks apps events metadata-manager
```

### Database Connection Issues

```bash
# Test database connection locally
export DATABASE_URL="postgresql://..."
cd backend
./venv/bin/python -c "
from sqlalchemy import create_engine, text
engine = create_engine('$DATABASE_URL')
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM users'))
    print(f'Users: {result.scalar()}')
"
```

## Monitoring

### Check Application Health

```bash
# Health endpoint (requires Databricks authentication)
curl https://your-app-url/health

# API info
curl https://your-app-url/api/info
```

### View Application Metrics

```sql
-- In Databricks SQL
SELECT * FROM arao.metadata_manager.v_user_activity;
SELECT * FROM arao.metadata_manager.audit_logs ORDER BY created_at DESC LIMIT 100;
SELECT status, COUNT(*) FROM arao.metadata_manager.comment_suggestions GROUP BY status;
```

## Updating the Application

To deploy changes:

```bash
# Make your code changes, then deploy
python deploy_to_databricks.py

# The app will automatically restart with new code
```

No need for `--hard-redeploy` unless you want to completely recreate the app.
