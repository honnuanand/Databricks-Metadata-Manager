-- =============================================================================
-- Lakebase Service Principal OAuth Setup Script
-- =============================================================================
-- This script sets up OAuth authentication for a Databricks service principal
-- to connect to Lakebase (Databricks PostgreSQL) without a static password.
--
-- Prerequisites:
-- 1. You must have admin access to the Lakebase instance
-- 2. You need the service principal's client_id from Databricks Apps
--
-- Usage:
-- 1. Connect to Lakebase as an admin user (e.g., via DBeaver, psql)
-- 2. Replace <SP_CLIENT_ID> with your actual service principal client ID
-- 3. Run this script
-- =============================================================================

-- Configuration: Replace with your actual service principal client ID
-- Example: 10922e0f-2688-4911-9fe0-4f35af5a563f
\set sp_client_id '10922e0f-2688-4911-9fe0-4f35af5a563f'

-- =============================================================================
-- Step 1: Create the databricks_auth extension (if not exists)
-- =============================================================================
-- This extension provides the databricks_create_role function for OAuth auth
CREATE EXTENSION IF NOT EXISTS databricks_auth;

-- Verify extension is installed
SELECT extname, extversion FROM pg_extension WHERE extname = 'databricks_auth';

-- =============================================================================
-- Step 2: Create Postgres role for the Service Principal
-- =============================================================================
-- This maps the SP's client_id to a Postgres role
-- The role name will be the client_id itself
SELECT databricks_create_role(:'sp_client_id', 'SERVICE_PRINCIPAL');

-- =============================================================================
-- Step 3: Grant database permissions to the SP role
-- =============================================================================
-- Grant connect to the database
GRANT CONNECT ON DATABASE databricks_postgres TO :"sp_client_id";

-- Grant usage on public schema
GRANT USAGE ON SCHEMA public TO :"sp_client_id";

-- Grant all privileges on all existing tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO :"sp_client_id";

-- Grant all privileges on all sequences (for auto-increment columns)
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO :"sp_client_id";

-- =============================================================================
-- Step 4: Set default privileges for future tables
-- =============================================================================
-- This ensures the SP can access tables created in the future
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON TABLES TO :"sp_client_id";

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON SEQUENCES TO :"sp_client_id";

-- =============================================================================
-- Step 5: Verify the setup
-- =============================================================================
-- Check that the role was created
SELECT rolname, rolcanlogin FROM pg_roles WHERE rolname = :'sp_client_id';

-- List all grants to the role
SELECT
    grantee,
    table_schema,
    table_name,
    privilege_type
FROM information_schema.table_privileges
WHERE grantee = :'sp_client_id'
ORDER BY table_schema, table_name;

-- =============================================================================
-- Done! The service principal can now use OAuth to connect to Lakebase.
-- =============================================================================
--
-- How it works:
-- 1. The app running in Databricks Apps has DATABRICKS_CLIENT_ID and
--    DATABRICKS_CLIENT_SECRET environment variables set automatically
-- 2. The app calls WorkspaceClient().database.generate_database_credential()
--    to get a short-lived OAuth token (valid for 1 hour)
-- 3. The app connects to Lakebase using:
--    - Username: <SP_CLIENT_ID>
--    - Password: <OAuth token>
-- 4. Lakebase validates the token and maps it to the Postgres role
--
-- Benefits:
-- - No long-lived passwords to manage or rotate
-- - Tokens auto-expire after 1 hour
-- - Better audit trail (SP identity in logs)
-- - Follows Databricks security best practices
-- =============================================================================
