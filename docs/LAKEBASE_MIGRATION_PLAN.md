# Migration Plan: Neon PostgreSQL → Databricks Lakebase

## Table of Contents

1. [Current Architecture Summary](#current-architecture-summary)
2. [Key Difference: Password Management](#key-difference-password-management)
3. [Migration Phases](#migration-phases)
   - [Phase 1: Lakebase Instance Setup](#phase-1-lakebase-instance-setup)
   - [Phase 2: Choose Authentication Strategy](#phase-2-choose-authentication-strategy)
   - [Phase 3: Code Changes](#phase-3-code-changes)
   - [Phase 4: Schema Migration](#phase-4-schema-migration)
   - [Phase 5: Databricks Secrets Update](#phase-5-databricks-secrets-update)
   - [Phase 6: Update app.yaml](#phase-6-update-appyaml)
4. [Password Flow Comparison](#password-flow-comparison)
5. [Migration Summary](#migration-summary)
6. [References](#references)

---

## Current Architecture Summary

Your app uses **Neon PostgreSQL** with:

| Component | Details |
|-----------|---------|
| **Tables** | `users`, `comments`, `approvals`, `audit_logs`, `alembic_version` |
| **Password Storage** | Bcrypt hashing (`passlib`) stored in `users.hashed_password` |
| **JWT Tokens** | HS256 with python-jose for session management |
| **Connection** | SQLAlchemy with NullPool (serverless optimized) |
| **Database URL Format** | `postgresql://user:pass@ep-xxx.aws.neon.tech/neondb?sslmode=require` |

### Current Database Schema

```
backend/
├── app/
│   ├── models/
│   │   ├── user.py          # Users with bcrypt hashed passwords
│   │   ├── comment.py       # Comment suggestions
│   │   ├── approval.py      # Approval workflow
│   │   └── audit_log.py     # Audit trail
│   ├── db/
│   │   └── session.py       # SQLAlchemy session with NullPool
│   └── core/
│       ├── config.py        # DATABASE_URL configuration
│       └── security.py      # Bcrypt password hashing
```

---

## Key Difference: Password Management

### Two Types of Passwords to Understand

| Type | Neon PostgreSQL | Databricks Lakebase |
|------|-----------------|---------------------|
| **Database Connection Auth** | Static connection string with password | OAuth tokens (1-hour expiry) OR Native Postgres roles |
| **App User Auth** | Bcrypt hashed passwords in `users` table | **Same - no change needed** |
| **Connection Pooling** | NullPool (serverless) | Same pattern works |

### Important Distinction

- **Database connection authentication** (how your app connects to the DB) → **This changes**
- **Application user authentication** (how users log into your app) → **This stays the same**

Your users will still authenticate with bcrypt-hashed passwords stored in the `users` table. The JWT token flow remains identical. Only the database connection method changes.

---

## Migration Phases

### Phase 1: Lakebase Instance Setup

#### 1.1 Create Lakebase Instance

1. Navigate to **Compute → Database instances → Create** in Databricks workspace
2. Choose appropriate size and region
3. Note the instance name and connection details

#### 1.2 Enable Native Postgres Role Login

This is recommended for your use case as it allows persistent passwords instead of 1-hour OAuth tokens.

1. Edit instance settings
2. Enable **"Postgres Native Role Login"**
3. Save changes

#### 1.3 Create Application Role

Connect to Lakebase and run:

```sql
-- Create application role with password
CREATE ROLE metadata_manager_app LOGIN PASSWORD 'your-strong-password-here';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE postgres TO metadata_manager_app;

-- Grant schema privileges
GRANT ALL PRIVILEGES ON SCHEMA public TO metadata_manager_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO metadata_manager_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO metadata_manager_app;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON TABLES TO metadata_manager_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON SEQUENCES TO metadata_manager_app;
```

---

### Phase 2: Choose Authentication Strategy

#### Option A: Native Postgres Role (Recommended)

**Pros:**
- Persistent password stored in Databricks secrets
- No token rotation needed
- Same connection pattern as Neon
- Simpler implementation

**Cons:**
- Password must be rotated manually
- Less granular than OAuth

**Best for:** Databricks Apps, internal applications

#### Option B: OAuth Token with Auto-Refresh

**Pros:**
- More secure (tokens expire hourly)
- Uses Databricks identity
- Better audit trail

**Cons:**
- Requires token refresh logic
- More complex implementation
- May cause connection issues if token expires mid-session

**Best for:** External applications, high-security requirements

### Recommendation

Use **Option A (Native Postgres Role)** for your Databricks App deployment. It provides the simplest migration path with minimal code changes.

---

### Phase 3: Code Changes

#### 3.1 Update Configuration

**File: `backend/app/core/config.py`**

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Existing settings...

    # Legacy Neon support (for local development)
    DATABASE_URL: Optional[str] = None

    # Lakebase configuration
    LAKEBASE_HOST: str = ""
    LAKEBASE_PORT: int = 5432
    LAKEBASE_DATABASE: str = "postgres"
    LAKEBASE_USER: str = ""
    LAKEBASE_PASSWORD: str = ""

    @property
    def effective_database_url(self) -> str:
        """Returns the appropriate database URL based on configuration."""
        # Use Lakebase if configured
        if self.LAKEBASE_HOST:
            return (
                f"postgresql://{self.LAKEBASE_USER}:{self.LAKEBASE_PASSWORD}"
                f"@{self.LAKEBASE_HOST}:{self.LAKEBASE_PORT}"
                f"/{self.LAKEBASE_DATABASE}?sslmode=require"
            )
        # Fallback to legacy DATABASE_URL for local development
        if self.DATABASE_URL:
            return self.DATABASE_URL
        raise ValueError("No database configuration found")

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
```

#### 3.2 Update Database Session

**File: `backend/app/db/session.py`**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Create engine with Lakebase-compatible settings
engine = create_engine(
    settings.effective_database_url,
    poolclass=NullPool,  # Required for serverless/Lakebase
    connect_args={
        "connect_timeout": 10,
        "sslmode": "require"
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency for FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### 3.3 (Optional) OAuth Token Authentication

If you choose OAuth instead of native roles, add this module:

**File: `backend/app/core/lakebase_auth.py`**

```python
from databricks.sdk import WorkspaceClient
import uuid
from datetime import datetime, timedelta
from typing import Optional
import threading

class LakebaseAuthManager:
    """Manages OAuth token authentication for Lakebase."""

    _instance: Optional['LakebaseAuthManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._instance_name: str = ""
        self._initialized = True

    def configure(self, instance_name: str):
        """Configure the auth manager with Lakebase instance name."""
        self._instance_name = instance_name

    def get_token(self) -> str:
        """Get a valid OAuth token, refreshing if necessary."""
        # Return cached token if still valid (with 5-minute buffer)
        if self._token and self._token_expiry:
            if self._token_expiry > datetime.now() + timedelta(minutes=5):
                return self._token

        # Generate new token
        w = WorkspaceClient()
        cred = w.database.generate_database_credential(
            request_id=str(uuid.uuid4()),
            instance_names=[self._instance_name]
        )

        self._token = cred.token
        self._token_expiry = datetime.now() + timedelta(minutes=55)
        return self._token

    def get_connection_string(self, host: str, port: int, database: str, user: str) -> str:
        """Get a connection string with fresh OAuth token as password."""
        token = self.get_token()
        return (
            f"postgresql://{user}:{token}@{host}:{port}/{database}?sslmode=require"
        )

# Singleton instance
lakebase_auth = LakebaseAuthManager()
```

**Updated session.py for OAuth:**

```python
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.lakebase_auth import lakebase_auth

def get_database_url() -> str:
    """Get database URL with fresh OAuth token if using Lakebase OAuth."""
    if settings.LAKEBASE_HOST and settings.USE_OAUTH:
        lakebase_auth.configure(settings.LAKEBASE_INSTANCE)
        return lakebase_auth.get_connection_string(
            host=settings.LAKEBASE_HOST,
            port=settings.LAKEBASE_PORT,
            database=settings.LAKEBASE_DATABASE,
            user=settings.LAKEBASE_USER
        )
    return settings.effective_database_url

# For OAuth, create engine factory pattern
def create_db_engine():
    return create_engine(
        get_database_url(),
        poolclass=NullPool,
        connect_args={"connect_timeout": 10, "sslmode": "require"}
    )

engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

---

### Phase 4: Schema Migration

#### 4.1 Create Tables in Lakebase

Connect to your Lakebase instance via SQL Editor or psql and run:

```sql
-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USERS TABLE
-- ============================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('SUGGEST_ONLY', 'APPROVER', 'ADMIN')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);

-- ============================================
-- COMMENTS TABLE
-- ============================================
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('CATALOG', 'SCHEMA', 'TABLE', 'COLUMN')),
    entity_catalog VARCHAR(255) NOT NULL,
    entity_schema VARCHAR(255),
    entity_table VARCHAR(255),
    entity_column VARCHAR(255),
    current_comment TEXT,
    suggested_comment TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'APPLIED')),
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    submitted_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_comments_status ON comments(status);
CREATE INDEX idx_comments_created_by ON comments(created_by);
CREATE INDEX idx_comments_entity_type ON comments(entity_type);
CREATE INDEX idx_comments_entity_catalog ON comments(entity_catalog);

-- ============================================
-- APPROVALS TABLE
-- ============================================
CREATE TABLE approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id UUID NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
    approver_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    action VARCHAR(20) NOT NULL CHECK (action IN ('APPROVED', 'REJECTED', 'REQUEST_CHANGES')),
    feedback TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_approvals_comment_id ON approvals(comment_id);
CREATE INDEX idx_approvals_approver_id ON approvals(approver_id);

-- ============================================
-- AUDIT LOGS TABLE
-- ============================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- ============================================
-- ALEMBIC VERSION TABLE (for migrations)
-- ============================================
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Insert current migration version
INSERT INTO alembic_version (version_num) VALUES ('b2433408b2f5');
```

#### 4.2 Seed Initial Users

```sql
-- Insert seed users with bcrypt hashed passwords
-- Password hashes generated with: passlib.hash.bcrypt.hash("password")

INSERT INTO users (id, email, username, full_name, hashed_password, role, is_active, is_superuser)
VALUES
    (
        '00000000-0000-0000-0000-000000000001',
        'admin@example.com',
        'admin',
        'Admin User',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VttYdGvN1bqvlC', -- admin123
        'ADMIN',
        TRUE,
        TRUE
    ),
    (
        '00000000-0000-0000-0000-000000000002',
        'approver@example.com',
        'approver',
        'Approver User',
        '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', -- approver123
        'APPROVER',
        TRUE,
        FALSE
    ),
    (
        '00000000-0000-0000-0000-000000000003',
        'user@example.com',
        'testuser',
        'Test User',
        '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', -- user123
        'SUGGEST_ONLY',
        TRUE,
        FALSE
    );
```

#### 4.3 Data Migration (If Needed)

If you have existing data in Neon to migrate:

```bash
# Export from Neon
pg_dump -h ep-xxx.aws.neon.tech -U username -d neondb \
  --data-only --no-owner --no-privileges \
  -t users -t comments -t approvals -t audit_logs \
  > neon_data_export.sql

# Import to Lakebase
psql -h your-instance.lakebase.databricks.com -U metadata_manager_app -d postgres \
  -f neon_data_export.sql
```

---

### Phase 5: Databricks Secrets Update

#### 5.1 Remove Old Neon Secrets

```bash
# List existing secrets
databricks secrets list-secrets metadata-manager

# Remove Neon database URL
databricks secrets delete-secret metadata-manager database-url
```

#### 5.2 Add Lakebase Secrets

```bash
# Add Lakebase host
databricks secrets put-secret metadata-manager lakebase-host \
  --string-value "your-instance-id.lakebase.cloud.databricks.com"

# Add Lakebase password
databricks secrets put-secret metadata-manager lakebase-password \
  --string-value "your-strong-password-here"

# Add Lakebase user (optional, can be in app.yaml)
databricks secrets put-secret metadata-manager lakebase-user \
  --string-value "metadata_manager_app"
```

#### 5.3 Verify Secrets

```bash
databricks secrets list-secrets metadata-manager
```

---

### Phase 6: Update app.yaml

**File: `app.yaml`**

```yaml
command:
  - /bin/bash
  - -c
  - |
    cd /app/backend && \
    pip install -r requirements.txt && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000

env:
  # Lakebase Configuration
  - name: LAKEBASE_HOST
    valueFrom: "{{secrets/metadata-manager/lakebase-host}}"
  - name: LAKEBASE_PASSWORD
    valueFrom: "{{secrets/metadata-manager/lakebase-password}}"
  - name: LAKEBASE_USER
    value: "metadata_manager_app"
  - name: LAKEBASE_DATABASE
    value: "postgres"
  - name: LAKEBASE_PORT
    value: "5432"

  # Application Settings
  - name: SECRET_KEY
    valueFrom: "{{secrets/metadata-manager/secret-key}}"
  - name: ALGORITHM
    value: "HS256"
  - name: ACCESS_TOKEN_EXPIRE_MINUTES
    value: "480"

  # Databricks Configuration
  - name: DATABRICKS_HOST
    value: "{{databricks_host}}"
  - name: DATABRICKS_TOKEN
    valueFrom: "{{secrets/metadata-manager/databricks-token}}"

  # CORS
  - name: CORS_ORIGINS
    value: "*"
```

---

## Password Flow Comparison

### Database Connection Authentication

```
BEFORE (Neon PostgreSQL):
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│   FastAPI App                                                          │
│       │                                                                │
│       │  Static connection string                                      │
│       │  postgresql://user:PASSWORD@ep-xxx.neon.tech/db               │
│       │  (password never changes, stored in secrets)                   │
│       ▼                                                                │
│   Neon PostgreSQL                                                      │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘

AFTER (Lakebase - Native Role) [RECOMMENDED]:
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│   FastAPI App                                                          │
│       │                                                                │
│       │  Static connection string                                      │
│       │  postgresql://role:PASSWORD@instance.lakebase.com/db          │
│       │  (password for native Postgres role, same pattern as Neon)     │
│       ▼                                                                │
│   Databricks Lakebase                                                  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘

AFTER (Lakebase - OAuth):
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│   FastAPI App                                                          │
│       │                                                                │
│       │  1. Generate OAuth token (databricks-sdk)                      │
│       │  2. Token valid for 1 hour                                     │
│       │  3. Use token as password in connection string                 │
│       │  postgresql://user:OAUTH_TOKEN@instance.lakebase.com/db       │
│       ▼                                                                │
│   Databricks Lakebase                                                  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Application User Authentication (NO CHANGE)

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│   User Login Flow (IDENTICAL for Neon and Lakebase)                   │
│                                                                        │
│   Browser                                                              │
│       │                                                                │
│       │  POST /api/v1/auth/login                                      │
│       │  { "username": "admin", "password": "admin123" }              │
│       ▼                                                                │
│   FastAPI Backend                                                      │
│       │                                                                │
│       │  1. Query users table: SELECT * FROM users WHERE username=?   │
│       │  2. Get hashed_password from database                          │
│       │  3. Verify: bcrypt.verify("admin123", hashed_password)        │
│       │  4. Generate JWT token if valid                                │
│       ▼                                                                │
│   Return JWT Token                                                     │
│       │                                                                │
│       │  { "access_token": "eyJ...", "token_type": "bearer" }        │
│       ▼                                                                │
│   Browser stores token, uses for subsequent requests                   │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘

YOUR APP'S USER AUTHENTICATION IS UNCHANGED!
- Bcrypt password hashing: SAME
- JWT token generation: SAME
- User table schema: SAME
- Login/logout flow: SAME
```

---

## Migration Summary

### What Changes

| Component | Change Required | Effort |
|-----------|-----------------|--------|
| Database connection string | Update format for Lakebase | Low |
| `config.py` | Add Lakebase config properties | Low |
| `session.py` | Minor updates for connection | Low |
| Databricks Secrets | Replace Neon with Lakebase secrets | Low |
| `app.yaml` | Update environment variables | Low |
| Schema | Recreate tables in Lakebase | Medium |
| Data | Export/import if existing data | Medium |

### What Stays the Same

| Component | Status |
|-----------|--------|
| User password hashing (bcrypt) | **No change** |
| JWT token generation | **No change** |
| SQLAlchemy models | **No change** |
| API endpoints | **No change** |
| Frontend authentication | **No change** |
| Role-based permissions | **No change** |

### Estimated Total Effort

**2-4 hours** for complete migration including:
- Lakebase instance setup: 30 min
- Code changes: 30 min
- Schema creation: 30 min
- Secrets configuration: 15 min
- Testing: 1-2 hours

---

## Pre-Migration Checklist

- [ ] Lakebase instance created in Databricks workspace
- [ ] Native Postgres Role Login enabled
- [ ] Application role created with appropriate permissions
- [ ] Code changes implemented and tested locally
- [ ] Schema created in Lakebase
- [ ] Seed data inserted (or production data migrated)
- [ ] Databricks secrets updated
- [ ] app.yaml updated
- [ ] Local testing with Lakebase connection successful
- [ ] Deployment to Databricks Apps successful
- [ ] End-to-end authentication flow tested

---

## Rollback Plan

If issues occur, rollback by:

1. Revert `app.yaml` to use Neon secrets
2. Restore original `config.py` and `session.py`
3. Re-add Neon secrets to Databricks:
   ```bash
   databricks secrets put-secret metadata-manager database-url \
     --string-value "postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require"
   ```
4. Redeploy application

---

## References

- [Databricks Lakebase Authentication Documentation](https://docs.databricks.com/aws/en/oltp/instances/authentication)
- [Lakebase Authentication and Permissions](https://docs.databricks.com/aws/en/oltp/instances/auth-and-permissions)
- [Lakebase Data API](https://docs.databricks.com/aws/en/oltp/projects/data-api)
- [How to use Lakebase as a transactional data layer for Databricks Apps](https://www.databricks.com/blog/how-use-lakebase-transactional-data-layer-databricks-apps)
- [Lakebase Product Page](https://www.databricks.com/product/lakebase)
- [Lakebase with Databricks Identity (Medium)](https://guha-ayan.medium.com/lakebase-how-to-connect-use-with-databricks-identity-ac668dc19927)
