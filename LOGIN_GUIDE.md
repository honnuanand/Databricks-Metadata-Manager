# Login Guide - Metadata Manager

## Two-Layer Authentication Model

This application uses a **two-layer security model**:

1. **Layer 1: Databricks Workspace Authentication** (enforced by Databricks Apps platform)
2. **Layer 2: Application Authentication** (custom user accounts with PostgreSQL/Neon)

## How to Access the Application

### Step 1: Authenticate to Databricks Workspace

1. Open the app URL in your browser:
   ```
   https://metadata-manager-2409307273843806.aws.databricksapps.com
   ```

2. You'll be redirected to Databricks login page:
   ```
   https://fe-vm-leaps-fe.cloud.databricks.com/login.html
   ```

3. **Login with your Databricks workspace credentials**
   - Use your Databricks username/password
   - Or use SSO if configured for your workspace

4. After successful Databricks authentication, you'll be redirected back to the app

### Step 2: Login to the Application

Once past the Databricks auth, you'll see our **custom login page** with email/password fields.

**Use these application credentials:**

- **Admin User**
  - Email: `admin@example.com`
  - Password: `admin123`
  - Role: ADMIN (full access)

- **Approver User**
  - Email: `approver@example.com`
  - Password: `approver123`
  - Role: APPROVER (can approve/apply comments)

- **Regular User**
  - Email: `user@example.com`
  - Password: `user123`
  - Role: SUGGEST_ONLY (can create suggestions)

## Why Two Layers?

This security model ensures:
- ✅ Only authorized Databricks workspace users can access the app
- ✅ Fine-grained role-based access control within the app
- ✅ Audit trail of who accessed what
- ✅ Integration with your organization's Databricks security

## For Testing/Development

### Browser Testing
Browser-based tests (Playwright UI tests) require manual Databricks login first, so they're skipped in automated CI/CD.

### API Testing
API endpoints also require Databricks authentication tokens. To test:

1. Login to the app in your browser
2. Open browser DevTools → Application → Cookies
3. Copy the Databricks session cookie
4. Use it in API requests

### Local Development
For local development without Databricks Apps:
```bash
# Backend
cd backend
./venv/bin/uvicorn app.main:app --reload --port 8080

# Frontend
cd front-end
VITE_API_URL=http://localhost:8080 npm run dev
```

Local development bypasses Databricks authentication and only uses application-level auth.

## Troubleshooting

**Problem**: Stuck on Databricks login page
- **Solution**: Contact your Databricks workspace admin to get access

**Problem**: Can't login with application credentials
- **Solution**: Ensure you've passed Databricks auth first. Check the URL - if it contains `databricks.com`, you're still on layer 1.

**Problem**: 401 Unauthorized after login
- **Solution**: Check that the database is seeded with users. Run:
  ```bash
  cd backend
  export DATABASE_URL="postgresql://..."
  ./venv/bin/python seed_database.py
  ```

## Database Connection

The application connects to Neon PostgreSQL database with these credentials stored in Databricks secrets:
- Secret Scope: `metadata-manager-secrets`
- Secret Key: `database-url`

Connection string format:
```
postgresql://neondb_owner:npg_SaRbXP4x6wtj@ep-lively-mud-a4u1i94u.us-east-1.aws.neon.tech/neondb?sslmode=require
```
