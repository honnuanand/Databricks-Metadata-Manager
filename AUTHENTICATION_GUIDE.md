# Databricks Metadata Manager - Authentication System Guide

## Overview

This document provides a comprehensive guide to the authentication system implementation, troubleshooting steps, and lessons learned during development.

## Table of Contents

1. [Authentication Flow](#authentication-flow)
2. [Issues Encountered and Solutions](#issues-encountered-and-solutions)
3. [Testing Infrastructure](#testing-infrastructure)
4. [Configuration](#configuration)
5. [Troubleshooting](#troubleshooting)

---

## Authentication Flow

### High-Level Architecture

```
User Login
    ↓
Neon PostgreSQL Database Authentication
    ↓
JWT Token Generation (Access + Refresh)
    ↓
Token Storage (localStorage)
    ↓
API Requests with Bearer Token
    ↓
Token Verification → User Object
```

### Components

1. **Frontend** (`/front-end/src`)
   - `services/auth.service.ts` - Authentication API calls
   - `store/authSlice.ts` - Redux state management
   - `services/api.ts` - Axios instance with interceptors

2. **Backend** (`/backend/app`)
   - `services/auth_service.py` - JWT token management
   - `services/user_service.py` - User authentication against PostgreSQL
   - `api/dependencies/auth.py` - FastAPI authentication dependencies
   - `api/endpoints/auth.py` - Login/logout endpoints

3. **Database**
   - **Neon PostgreSQL** - Serverless PostgreSQL for user storage
   - Users table with bcrypt password hashing
   - Roles: `admin`, `approver`, `suggest_only`

---

## Issues Encountered and Solutions

### Issue 1: 401 Unauthorized on Login ❌ → ✅ FIXED

**Problem:**
```
Failed to load resource: the server responded with a status of 401 ()
```

**Root Cause:**
`user_service.py` was using hardcoded mock users instead of querying the Neon PostgreSQL database.

**Solution:**
Updated `authenticate_user()` to query the database:

```python
async def authenticate_user(self, username: str, password: str) -> Optional[User]:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, email, username, full_name, hashed_password, role, is_active, is_superuser, created_at, updated_at
            FROM users
            WHERE email = :identifier OR username = :identifier
        """), {"identifier": username})

        row = result.fetchone()
        if not row:
            return None

        if not pwd_context.verify(password, row[4]):
            return None
```

**Files Modified:**
- `/backend/app/services/user_service.py`

---

### Issue 2: Role Mismatch ❌ → ✅ FIXED

**Problem:**
Permissions not working correctly even after database authentication.

**Root Cause:**
Database stores roles in UPPERCASE (`ADMIN`, `APPROVER`, `SUGGEST_ONLY`) but permission checks expected lowercase (`admin`, `approver`, `suggest_only`).

**Solution:**
Added role normalization:

```python
role = row[5].lower() if row[5] else None
if role == 'suggest_only':
    role = 'suggest_only'  # Map SUGGEST_ONLY → suggest_only
```

**Files Modified:**
- `/backend/app/services/user_service.py` (lines 75-78)

---

### Issue 3: Database Connection Pooling Issues ❌ → ✅ FIXED

**Problem:**
503 Service Unavailable errors, connection exhaustion.

**Root Cause:**
Creating new database engine on every request, overwhelming the serverless Neon database.

**Solution:**
Implemented singleton engine pattern with NullPool:

```python
_engine = None

def get_engine():
    """Get or create the database engine singleton"""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL,
            poolclass=NullPool,  # Disable connection pooling for serverless
            connect_args={"connect_timeout": 10}
        )
    return _engine
```

**Files Modified:**
- `/backend/app/services/user_service.py` (lines 15-32)

---

### Issue 4: Backend Routes Not Accessible ❌ → ✅ FIXED

**Problem:**
`/health` and `/api/*` endpoints returning HTML (React app) instead of JSON.

**Root Cause:**
FastAPI's catch-all route `/{full_path:path}` was defined **before** API endpoints, intercepting all requests.

**Solution:**
Reordered routes in `main.py`:

```python
# Correct Order:
@app.get("/health")          # 1. Specific routes first
@app.get("/api/info")         # 2. API routes
@app.get("/")                 # 3. Root serves React
@app.get("/{full_path:path}") # 4. Catch-all LAST
```

**Files Modified:**
- `/backend/app/main.py` (moved `/health` endpoint before catch-all)

---

### Issue 5: DATABASE_URL Not Injected ❌ → ✅ FIXED

**Problem:**
Backend using default DATABASE_URL (`postgresql://user:pass@localhost/dbname`) instead of Neon database.

**Root Cause:**
Databricks Apps `valueFrom` secret references weren't working. The app.yaml was configured as:

```yaml
env:
  - name: DATABASE_URL
    valueFrom: metadata-manager-secrets/database-url
```

But the environment variable wasn't being populated.

**Solution:**
Changed deployment script to retrieve secret value and inject as direct value:

```python
# Get DATABASE_URL from Databricks secrets
result = subprocess.run(
    ['databricks', 'secrets', 'get-secret', 'metadata-manager-secrets', 'database-url', '--output', 'json'],
    capture_output=True, text=True, check=True
)
secret_data = json.loads(result.stdout)
database_url = base64.b64decode(secret_data['value']).decode('utf-8')

# Inject as direct value in app.yaml
f.write('  - name: DATABASE_URL\n')
f.write(f'    value: "{database_url}"\n')
```

**Files Modified:**
- `/deploy_to_databricks.py` (lines 371-426)

---

### Issue 6: bcrypt Version Incompatibility ❌ → ✅ FIXED

**Problem:**
Passwords failing verification in production despite working locally.

**Root Cause:**
bcrypt 5.x is incompatible with passlib 1.7.4. Production was installing bcrypt 5.x, but password hashes were created with bcrypt 4.x.

**Solution:**
Pinned bcrypt version in `requirements.txt`:

```txt
passlib[bcrypt]==1.7.4
bcrypt==4.1.3  # ← Added explicit version pin
```

**Files Modified:**
- `/backend/requirements.txt`

---

### Issue 7: FastAPI HTTPBearer Returns 403 Instead of 401 ❌ → ✅ FIXED

**Problem:**
`/api/v1/auth/me` endpoint returning 403 Forbidden for authentication failures instead of 401 Unauthorized.

**Root Cause:**
FastAPI's `HTTPBearer()` security scheme returns **403 by default** when token is missing or invalid, but HTTP standards require 401 for authentication errors.

**Solution:**
Created custom HTTPBearer class that converts 403 to 401:

```python
class HTTPBearerCustom(HTTPBearer):
    """Custom HTTPBearer that returns 401 instead of 403"""
    async def __call__(self, request: Request):
        try:
            return await super().__call__(request)
        except HTTPException as e:
            # HTTPBearer raises 403 by default, change to 401
            if e.status_code == status.HTTP_403_FORBIDDEN:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            raise

security = HTTPBearerCustom()
```

**Files Modified:**
- `/backend/app/api/dependencies/auth.py` (lines 10-25)

---

### Issue 8: Axios Interceptor Overwrites Token Headers ❌ → ⚠️ PARTIALLY FIXED

**Problem:**
Tests explicitly providing fresh tokens still got 401 errors because old tokens from localStorage were being used.

**Root Cause:**
The axios request interceptor **always overwrites** the Authorization header:

```typescript
// Before - ALWAYS overwrites
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`  // Overwrites!
  }
})
```

**Solution Attempted:**
Modified interceptor to only add token if not already present:

```typescript
// After - Only adds if not set
api.interceptors.request.use((config) => {
  if (!config.headers.Authorization) {  // Check first
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
})
```

**Workaround for Tests:**
Tests use raw `axios` instance instead of `api` instance to bypass interceptor:

```typescript
// Bypass interceptor in tests
import axios from 'axios'

const meResponse = await axios.get('/api/v1/auth/me', {
  headers: { Authorization: `Bearer ${token}` }
})
```

**Files Modified:**
- `/front-end/src/services/api.ts` (lines 15-29)
- `/front-end/src/testing/tests/auth.tests.ts` (multiple tests)

**Status:** ⚠️ Tests still failing - deeper investigation needed into JWT token verification in production

---

## Testing Infrastructure

### In-App Test Runner

Created comprehensive test runner accessible inside Databricks SSO boundary.

**Location:** https://metadata-manager-2409307273843806.aws.databricksapps.com/test-runner

**Features:**
- ✅ Real-time test execution with progress bars
- ✅ Expandable test categories
- ✅ Copy results to clipboard (JSON format)
- ✅ Export test reports
- ✅ Visual indicators (✅ passed, ❌ failed)

**Test Categories:**
1. **Authentication** (15 tests)
   - Health check
   - Login (admin, approver, user)
   - Invalid credentials rejection
   - Token validation
   - Permission verification
   - Token persistence

2. **Catalogs & Schemas** (4 tests)
   - List catalogs
   - Get catalog details
   - List schemas
   - Browse permissions

**Files:**
- `/front-end/src/testing/TestRunner.tsx` - Main UI component
- `/front-end/src/testing/utils/testExecutor.ts` - Test execution engine
- `/front-end/src/testing/utils/assertions.ts` - Assertion library
- `/front-end/src/testing/tests/auth.tests.ts` - Authentication tests
- `/front-end/src/testing/tests/catalog.tests.ts` - Catalog tests

---

## Configuration

### Environment Variables

**Backend (`backend/app/core/config.py`):**

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://user:pass@localhost/dbname` | Neon PostgreSQL connection string |
| `SECRET_KEY` | `LrM0Shhrw0MhIzRtQhbUF30o4dTjE4d5m6PRDZhGUPM` | JWT signing key |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` (8 hours) | Access token expiry |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token expiry |

**Databricks Secrets:**

Secrets stored in `metadata-manager-secrets` scope:

```bash
databricks secrets put-secret metadata-manager-secrets database-url \
  --string-value "postgresql://neondb_owner:***@ep-lively-mud-a4u1i94u.us-east-1.aws.neon.tech/neondb?sslmode=require"

databricks secrets put-secret metadata-manager-secrets secret-key \
  --string-value "LrM0Shhrw0MhIzRtQhbUF30o4dTjE4d5m6PRDZhGUPM"
```

### Test Users

Three test users are seeded in the database:

| Email | Password | Role | Permissions |
|-------|----------|------|-------------|
| `admin@example.com` | `admin123` | `admin` | All permissions including user management |
| `approver@example.com` | `approver123` | `approver` | Can approve/apply suggestions |
| `user@example.com` | `user123` | `suggest_only` | Can only create suggestions |

**Seeding Script:** `/backend/seed_database.py`

```bash
DATABASE_URL='postgresql://...' python seed_database.py
```

---

## Troubleshooting

### Issue: Login Returns 401

**Check:**
1. Is DATABASE_URL configured correctly?
   ```bash
   databricks secrets get-secret metadata-manager-secrets database-url
   ```

2. Are users seeded in database?
   ```bash
   DATABASE_URL='...' python backend/seed_database.py
   ```

3. Check backend logs for authentication errors

**Common Causes:**
- Database connection failure
- Password hash mismatch (bcrypt version)
- User not found in database

---

### Issue: Token Verification Fails (401 on /me endpoint)

**Check:**
1. Is SECRET_KEY the same for token generation and verification?
2. Is token expired? (Check `exp` claim)
3. Check backend logs in `auth_service.py::verify_token()`

**Debug:**
```python
# Add to auth_service.py
logger.info(f"verify_token: Token starts with: {token[:30]}...")
logger.info(f"verify_token: SECRET_KEY starts with: {self.secret_key[:20]}...")
```

---

### Issue: Old Tokens Cause 403 Errors

**Solution:**
Clear browser localStorage and login again:

```javascript
// In browser console
localStorage.removeItem('access_token')
localStorage.removeItem('refresh_token')
```

**Why:** Old tokens signed with previous SECRET_KEY are invalid.

---

### Issue: Database Connection Errors

**Check Neon Database Status:**
```bash
psql "postgresql://neondb_owner:***@ep-lively-mud-a4u1i94u.us-east-1.aws.neon.tech/neondb?sslmode=require" -c "SELECT COUNT(*) FROM users"
```

**Common Causes:**
- Neon database suspended (auto-suspends after inactivity)
- Network connectivity issues
- SSL certificate problems (add `?sslmode=require`)

---

## Test Results

### Latest Test Run

**Date:** 2025-10-29
**Total Tests:** 19
**Passed:** 11 (58%)
**Failed:** 8 (42%)

**Passing Tests:** ✅
- Health Check - Database Status
- Login with Admin User
- Login with Approver User
- Login with Regular User
- Reject Invalid Credentials
- Verify Admin Permissions
- Verify Approver Permissions
- Verify User Permissions
- Reject Invalid Token
- Reject Expired Token
- Login Returns Refresh Token

**Failing Tests:** ❌
- Get Current User Info (401)
- Get Current User with Valid Token (401)
- Token Persists Across Requests (401)
- Each User Gets Their Own Token (401)
- List Catalogs (500)
- Get Catalog Details (500)
- List Schemas in Catalog (500)
- Regular User Can Browse Catalogs (500)

**Analysis:**
- Core authentication works (login, password verification, permissions)
- `/me` endpoint has token verification issues (needs investigation)
- Catalog endpoints failing (likely DATABRICKS_TOKEN not configured)

---

## Future Improvements

1. **Investigate `/me` endpoint failures**
   - Add more detailed logging to token verification
   - Compare token format between local and production
   - Verify SECRET_KEY matches between generation and verification

2. **Configure Databricks Token**
   - Set DATABRICKS_TOKEN in secrets for catalog access
   - Test Databricks SQL warehouse connectivity

3. **Add Refresh Token Flow**
   - Implement automatic token refresh on 401
   - Add refresh endpoint tests

4. **Add Log Collection**
   - Capture frontend console logs in test failures
   - Include backend logs in test reports
   - Automatic log aggregation for debugging

5. **Improve Error Messages**
   - More specific error details for 401/403
   - Include troubleshooting hints in error responses

---

## References

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Neon PostgreSQL](https://neon.tech/docs)
- [Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)

---

**Last Updated:** 2025-10-29
**Version:** 1.0.0
**Status:** Production (with known issues)
