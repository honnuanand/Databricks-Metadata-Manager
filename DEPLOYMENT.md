# Metadata Manager - Databricks Deployment Guide

## Prerequisites

1. **Databricks CLI** installed and configured
2. **Databricks Personal Access Token** (PAT) for the app

## Secret Scope Setup

A secret scope named `metadata-manager-secrets` has been created with the following secrets:

| Secret Key | Description | Status |
|------------|-------------|--------|
| `databricks-host` | Workspace URL | ✅ Added |
| `secret-key` | JWT signing key | ✅ Added |
| `databricks-token` | PAT for API access | ⏳ Needs to be added |

## Adding the Databricks Token

### Option 1: Generate a new PAT

1. Go to your Databricks workspace: https://fe-vm-leaps-fe.cloud.databricks.com
2. Click on your user icon (top right) → Settings
3. Click on "Developer" → "Access tokens"
4. Click "Generate new token"
5. Give it a name: `metadata-manager-app`
6. Set expiration (optional): 90 days recommended
7. Click "Generate"
8. **Copy the token immediately** (it won't be shown again)

### Option 2: Use existing token

If you have an existing token from another profile (like `e2-demo-field-eng`), you can use that.

### Add the token to the secret scope:

```bash
# Interactive method (will prompt for token)
databricks secrets put-secret metadata-manager-secrets databricks-token

# Or direct method
databricks secrets put-secret metadata-manager-secrets databricks-token --string-value "dapi..."
```

## Verify Secrets

```bash
# List all secrets in the scope
databricks secrets list-secrets metadata-manager-secrets
```

## Deploy the Application

Once all secrets are configured:

```bash
# Regular deployment
python3 deploy_to_databricks.py --skip-secrets

# Or hard redeploy (delete existing app first)
python3 deploy_to_databricks.py --skip-secrets --hard-redeploy
```

## Application Configuration

The app will use these environment variables from the secret scope:

- `DATABRICKS_HOST`: Your workspace URL
- `DATABRICKS_TOKEN`: PAT for API access
- `SECRET_KEY`: For JWT token generation

## Deployment Steps

The deployment script will:

1. ✅ Build the React frontend (`npm run build`)
2. ✅ Copy static files to backend
3. ✅ Package the backend code
4. ✅ Upload to Databricks workspace at `/Workspace/Users/anand.rao@databricks.com/metadata-manager`
5. ✅ Deploy as a Databricks App

## App URL

After deployment, access your app at:
- Check the output of the deployment script for the URL
- Or go to: Workspace → Apps → metadata-manager

## Troubleshooting

### Secrets not found
```bash
# List available scopes
databricks secrets list-scopes

# List secrets in scope
databricks secrets list-secrets metadata-manager-secrets
```

### Deployment fails
```bash
# Check if app exists
databricks apps list

# Delete and redeploy
python3 deploy_to_databricks.py --hard-redeploy --skip-secrets
```

### Check app logs
```bash
# Get app status
databricks apps get metadata-manager

# View app logs
databricks apps logs metadata-manager
```
