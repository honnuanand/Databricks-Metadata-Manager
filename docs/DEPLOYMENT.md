# Databricks Apps Deployment Guide

This guide covers deploying the Metadata Manager to Databricks Apps with Lakebase (PostgreSQL) OAuth authentication.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Databricks Workspace                        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │  Databricks App │───▶│    Lakebase     │    │   Unity     │ │
│  │  (FastAPI +     │    │  (PostgreSQL)   │    │  Catalog    │ │
│  │   React)        │    │                 │    │             │ │
│  │                 │    │  Schema:        │    │  Metadata   │ │
│  │  SP: auto-      │    │  metadata_      │    │  Discovery  │ │
│  │  assigned       │    │  manager        │    │             │ │
│  └────────┬────────┘    └────────▲────────┘    └──────▲──────┘ │
│           │                      │                     │        │
│           │   OAuth Token        │                     │        │
│           └──────────────────────┘                     │        │
│                                                        │        │
│           │   Databricks SDK                           │        │
│           └────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Existing Workspace (Redeploy)

```bash
python deploy_to_databricks.py --skip-secrets
```

### New Workspace (Full Setup)

```bash
# 1. Configure CLI profile
databricks auth login --host https://WORKSPACE.cloud.databricks.com --profile PROFILE_NAME

# 2. Edit app.yaml with your settings (see Configuration section)

# 3. Create secrets
databricks secrets create-scope --scope metadata-manager-secrets --profile PROFILE_NAME
databricks secrets put-secret --scope metadata-manager-secrets --key secret-key --profile PROFILE_NAME
databricks secrets put-secret --scope metadata-manager-secrets --key databricks-token --profile PROFILE_NAME

# 4. Create Lakebase schema
python scripts/migrate_neon_to_lakebase.py --profile PROFILE_NAME --schema metadata_manager --skip-data

# 5. Deploy app
python deploy_to_databricks.py --skip-secrets

# 6. Grant SP access to Lakebase
python scripts/grant_lakebase_sp_access.py --profile PROFILE_NAME --schema metadata_manager

# 7. Redeploy to apply permissions
python deploy_to_databricks.py --skip-secrets
```

---

## Configuration

### `app.yaml` Structure

```yaml
# Deployment metadata (stripped before upload - used by deploy script only)
deployment:
  app_name: "metadata-mgr"           # App name in Databricks
  profile: "fe-vm-leaps-fe"          # Databricks CLI profile

command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

env:
  # Lakebase Database (OAuth via auto-injected DATABRICKS_CLIENT_ID)
  - name: LAKEBASE_INSTANCE
    value: "arao-lb"                 # Your Lakebase instance name
  - name: LAKEBASE_HOST
    value: "instance-xxx.database.cloud.databricks.com"  # Lakebase hostname
  - name: LAKEBASE_SCHEMA
    value: "metadata_manager"        # PostgreSQL schema

  # Databricks Workspace
  - name: DATABRICKS_HOST
    value: "https://workspace.cloud.databricks.com"
  - name: DATABRICKS_WAREHOUSE_PATH
    value: "/sql/1.0/warehouses/abc123"

  # Secrets (from Databricks Secret Scope)
  - name: SECRET_KEY
    valueFrom: "metadata-manager-secrets/secret-key"
  - name: DATABRICKS_TOKEN
    valueFrom: "metadata-manager-secrets/databricks-token"
```

### Values to Update for New Workspace

| Variable | Where to Find | Example |
|----------|---------------|---------|
| `deployment.profile` | Your CLI profile name | `my-workspace` |
| `deployment.app_name` | Choose unique name | `metadata-mgr` |
| `LAKEBASE_INSTANCE` | Lakebase UI > Instance name | `my-lakebase` |
| `LAKEBASE_HOST` | Lakebase UI > Connection info | `instance-xxx.database.cloud.databricks.com` |
| `LAKEBASE_SCHEMA` | Choose schema name | `metadata_manager` |
| `DATABRICKS_HOST` | Workspace URL | `https://my-workspace.cloud.databricks.com` |
| `DATABRICKS_WAREHOUSE_PATH` | SQL Warehouse > Connection details | `/sql/1.0/warehouses/abc123` |

---

## Deploy Script

### Usage

```bash
# Basic deployment (uses app.yaml settings)
python deploy_to_databricks.py --skip-secrets

# Override settings
python deploy_to_databricks.py --app-name my-app --profile my-profile --skip-secrets

# Use different config file
python deploy_to_databricks.py --config app.yaml.prod --skip-secrets

# Hard redeploy (delete and recreate)
python deploy_to_databricks.py --hard-redeploy --skip-secrets
```

### What It Does

1. **Reads config** from `app.yaml` (app_name, profile from `deployment:` section)
2. **Builds frontend** (`npm run build` in `front-end/`)
3. **Copies static files** to `backend/static/`
4. **Packages backend** (excludes venv, tests, cache)
5. **Strips deployment metadata** from app.yaml before upload
6. **Imports to workspace** (`/Workspace/Users/{email}/{app_name}`)
7. **Deploys app** via `databricks apps deploy`

### Configuration Priority

1. CLI arguments (`--app-name`, `--profile`)
2. Environment variable (`DATABRICKS_APP_NAME`)
3. `app.yaml` deployment section

---

## Lakebase OAuth Authentication

### How It Works

Databricks Apps automatically inject these environment variables:
- `DATABRICKS_CLIENT_ID` - Service Principal client ID
- `DATABRICKS_CLIENT_SECRET` - Service Principal secret

The app uses these to:
1. Generate OAuth tokens via `WorkspaceClient().database.generate_database_credential()`
2. Connect to Lakebase using SP client_id as username and OAuth token as password
3. Auto-refresh tokens before expiry (5 minute buffer)

### Key Files

| File | Purpose |
|------|---------|
| `backend/app/db/lakebase_oauth.py` | OAuth token manager |
| `backend/app/db/session.py` | Database session with OAuth support |
| `backend/requirements.txt` | Uses `psycopg[binary]` (psycopg3) |

### Verify OAuth is Working

```bash
# Get OAuth token for API access
TOKEN=$(databricks auth token --profile PROFILE --output json | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Check health endpoint
curl -H "Authorization: Bearer $TOKEN" https://APP_URL/health
```

Expected response:
```json
{
  "status": "healthy",
  "using_oauth": true,
  "oauth_token_expires_in": 3599,
  "oauth_username": "38cfcbb5-54b4-49a5-8f5f-38535d127178",
  "database_user_count": 3
}
```

---

## Granting Lakebase Access to Service Principal

After deploying, the app's Service Principal needs PostgreSQL permissions.

### Using the Script

```bash
python scripts/grant_lakebase_sp_access.py \
  --profile PROFILE_NAME \
  --app-name metadata-mgr \
  --schema metadata_manager
```

### What It Does

1. Gets SP info from the Databricks App
2. Creates PostgreSQL role with SP client_id as name
3. Sets security label for OAuth: `SECURITY LABEL FOR databricks_auth ON ROLE "uuid" IS 'id=SP_ID,type=SERVICE_PRINCIPAL'`
4. Grants permissions: USAGE, SELECT, INSERT, UPDATE, DELETE on schema

### Manual SQL (if needed)

```sql
-- Replace with your SP's client_id and numeric SP ID
-- Get these from: databricks apps get APP_NAME --output json

-- 1. Create role
CREATE ROLE "38cfcbb5-54b4-49a5-8f5f-38535d127178" WITH LOGIN NOINHERIT;

-- 2. Set security label (CRITICAL for OAuth)
SECURITY LABEL FOR databricks_auth ON ROLE "38cfcbb5-54b4-49a5-8f5f-38535d127178"
  IS 'id=78440603301853,type=SERVICE_PRINCIPAL';

-- 3. Grant permissions
GRANT USAGE ON SCHEMA metadata_manager TO "38cfcbb5-54b4-49a5-8f5f-38535d127178";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA metadata_manager
  TO "38cfcbb5-54b4-49a5-8f5f-38535d127178";
ALTER DEFAULT PRIVILEGES IN SCHEMA metadata_manager
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "38cfcbb5-54b4-49a5-8f5f-38535d127178";
```

---

## Creating Lakebase Schema

### Using Migration Script

```bash
# Create schema and tables (no data)
python scripts/migrate_neon_to_lakebase.py --profile PROFILE --schema metadata_manager --skip-data

# Or with data migration from Neon
python scripts/migrate_neon_to_lakebase.py --profile PROFILE --schema metadata_manager
```

### Tables Created

| Table | Purpose |
|-------|---------|
| `users` | User accounts with hashed passwords |
| `comments` | Comment suggestions |
| `approvals` | Approval workflow records |
| `audit_logs` | Audit trail |
| `alembic_version` | Migration tracking |

### Default Test Users

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | admin |
| approver | approver123 | approver |
| testuser | user123 | suggest_only |

---

## Secrets Setup

### Required Secrets

| Secret Key | Description |
|------------|-------------|
| `secret-key` | JWT signing key for app authentication |
| `databricks-token` | PAT token for Unity Catalog access |

### Create Secrets

```bash
# Create scope
databricks secrets create-scope --scope metadata-manager-secrets --profile PROFILE

# Add JWT secret (generate random)
databricks secrets put-secret --scope metadata-manager-secrets --key secret-key \
  --string-value "$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  --profile PROFILE

# Add Databricks token
databricks secrets put-secret --scope metadata-manager-secrets --key databricks-token \
  --string-value "dapi..." --profile PROFILE
```

### Verify Secrets

```bash
databricks secrets list-secrets --scope metadata-manager-secrets --profile PROFILE
```

---

## Troubleshooting

### "permission denied for table users"

**Cause**: SP doesn't have Lakebase permissions.

**Fix**: Run the grant script and redeploy:
```bash
python scripts/grant_lakebase_sp_access.py --profile PROFILE --schema metadata_manager
python deploy_to_databricks.py --skip-secrets
```

### "No module named 'psycopg'"

**Cause**: Wrong PostgreSQL driver.

**Fix**: Ensure `requirements.txt` has:
```
psycopg[binary]==3.2.3
```
(Not `psycopg2-binary`)

### "using_oauth: false" in health check

**Cause**: `DATABRICKS_CLIENT_ID` not detected.

**Check**:
1. App is running in Databricks Apps (not locally)
2. `LAKEBASE_INSTANCE` and `LAKEBASE_HOST` are set in app.yaml

### "connection to localhost refused"

**Cause**: Schema not set in database URL.

**Fix**: Ensure `session.py` passes schema to `get_database_url()`:
```python
database_url = oauth_mgr.get_database_url(schema=os.environ.get('LAKEBASE_SCHEMA'))
```

### App stuck in ERROR state

**Cause**: Often SP conflicts or resource issues.

**Fix**: Hard redeploy:
```bash
python deploy_to_databricks.py --hard-redeploy --skip-secrets
```

---

## Multi-Environment Setup

### Create Environment-Specific Configs

```bash
# Development
cp app.yaml app.yaml.dev

# Production
cp app.yaml app.yaml.prod
```

### Deploy to Different Environments

```bash
# Deploy to dev
python deploy_to_databricks.py --config app.yaml.dev --skip-secrets

# Deploy to prod
python deploy_to_databricks.py --config app.yaml.prod --skip-secrets
```

### Example: `app.yaml.prod`

```yaml
deployment:
  app_name: "metadata-mgr-prod"
  profile: "prod-workspace"

command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

env:
  - name: LAKEBASE_INSTANCE
    value: "prod-lakebase"
  - name: LAKEBASE_HOST
    value: "instance-prod.database.cloud.databricks.com"
  - name: LAKEBASE_SCHEMA
    value: "metadata_manager"
  - name: DATABRICKS_HOST
    value: "https://prod-workspace.cloud.databricks.com"
  # ... etc
```

---

## File Reference

| File | Purpose |
|------|---------|
| `app.yaml` | Main deployment configuration |
| `deploy_to_databricks.py` | Deployment script |
| `backend/app/db/lakebase_oauth.py` | OAuth token manager |
| `backend/app/db/session.py` | Database session factory |
| `backend/requirements.txt` | Python dependencies |
| `scripts/grant_lakebase_sp_access.py` | Grant SP permissions |
| `scripts/migrate_neon_to_lakebase.py` | Schema/data migration |
