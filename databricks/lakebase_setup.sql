-- ============================================================================
-- LAKEBASE SETUP FOR METADATA MANAGER
-- Instance Name: arao-lb
-- Instance Host: instance-f2a8b56a-7fe2-4c9c-a0a3-7768594a50e5.database.cloud.databricks.com
-- Database: databricks_postgres
-- ============================================================================
--
-- NOTE: Tables have been created by running: python databricks/setup_lakebase.py
--
-- This SQL file is provided for reference or manual setup.
-- Run this script while connected to your Lakebase instance as your
-- Databricks identity.
--
-- Connection:
--   psql "host=instance-f2a8b56a-7fe2-4c9c-a0a3-7768594a50e5.database.cloud.databricks.com \
--         user=anand.rao@databricks.com dbname=databricks_postgres port=5432 sslmode=require"
--
-- ============================================================================

-- ============================================================================
-- STEP 1: CREATE APPLICATION ROLE (Optional but recommended)
-- ============================================================================
-- This creates a native Postgres role for the application to use.
-- If you prefer OAuth, skip this step and configure the app to use OAuth tokens.

-- Uncomment and modify the password:
-- CREATE ROLE metadata_manager_app LOGIN PASSWORD 'your-strong-password-here';
-- GRANT ALL PRIVILEGES ON SCHEMA public TO metadata_manager_app;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO metadata_manager_app;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO metadata_manager_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO metadata_manager_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO metadata_manager_app;

-- ============================================================================
-- STEP 2: CREATE TABLES
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
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

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Comments table
CREATE TABLE IF NOT EXISTS comments (
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

CREATE INDEX IF NOT EXISTS idx_comments_status ON comments(status);
CREATE INDEX IF NOT EXISTS idx_comments_created_by ON comments(created_by);
CREATE INDEX IF NOT EXISTS idx_comments_entity_type ON comments(entity_type);
CREATE INDEX IF NOT EXISTS idx_comments_entity_catalog ON comments(entity_catalog);

-- Approvals table
CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id UUID NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
    approver_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    action VARCHAR(20) NOT NULL CHECK (action IN ('APPROVED', 'REJECTED', 'REQUEST_CHANGES')),
    feedback TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_approvals_comment_id ON approvals(comment_id);
CREATE INDEX IF NOT EXISTS idx_approvals_approver_id ON approvals(approver_id);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
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

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- Alembic version table
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INSERT INTO alembic_version (version_num)
VALUES ('b2433408b2f5')
ON CONFLICT (version_num) DO NOTHING;

-- ============================================================================
-- STEP 3: SEED INITIAL USERS
-- ============================================================================
-- These are bcrypt hashed passwords:
--   admin123    -> $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VttYdGvN1bqvlC
--   approver123 -> $2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi
--   user123     -> $2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW

INSERT INTO users (id, email, username, full_name, hashed_password, role, is_active, is_superuser)
VALUES
    (
        '00000000-0000-0000-0000-000000000001',
        'admin@example.com',
        'admin',
        'Admin User',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VttYdGvN1bqvlC',
        'ADMIN',
        TRUE,
        TRUE
    ),
    (
        '00000000-0000-0000-0000-000000000002',
        'approver@example.com',
        'approver',
        'Approver User',
        '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi',
        'APPROVER',
        TRUE,
        FALSE
    ),
    (
        '00000000-0000-0000-0000-000000000003',
        'user@example.com',
        'testuser',
        'Test User',
        '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
        'SUGGEST_ONLY',
        TRUE,
        FALSE
    )
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
SELECT 'Tables created:' as status;
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;

SELECT 'Users seeded:' as status;
SELECT id, email, username, role FROM users ORDER BY id;
