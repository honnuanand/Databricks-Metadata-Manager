# Databricks Schema Setup Instructions

Since you're already logged in to your Databricks workspace, here are the steps to create the metadata_manager schema:

## Option 1: Direct SQL Execution in Databricks Workspace

1. **Open your Databricks workspace**: https://e2-demo-field-eng.cloud.databricks.com/

2. **Create a SQL notebook or use SQL Editor**:
   - Go to "SQL" section in your workspace
   - Create a new SQL query/notebook

3. **Copy and paste this SQL script**:

```sql
-- ============================================================
-- Databricks Metadata Manager Schema Setup
-- Catalog: arao
-- Schema: metadata_manager
-- ============================================================

-- Create the metadata management schema
CREATE SCHEMA IF NOT EXISTS arao.metadata_manager
COMMENT 'Central repository for Databricks metadata management - tracks comment suggestions, approvals, and comprehensive audit logs';

-- Set the current schema
USE CATALOG arao;
USE SCHEMA metadata_manager;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id STRING NOT NULL COMMENT 'Unique identifier for the user',
    username STRING NOT NULL COMMENT 'Username for login',
    email STRING NOT NULL COMMENT 'User email address',
    full_name STRING COMMENT 'Full display name',
    role STRING NOT NULL COMMENT 'User role: suggest_only, approver, or admin',
    is_active BOOLEAN DEFAULT true COMMENT 'Whether the user account is active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Account creation timestamp',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Last update timestamp',
    CONSTRAINT pk_users PRIMARY KEY(user_id)
)
USING DELTA
COMMENT 'System users with role-based access for metadata management';

-- Create comment suggestions table
CREATE TABLE IF NOT EXISTS comment_suggestions (
    suggestion_id STRING NOT NULL COMMENT 'Unique identifier for the suggestion',
    entity_type STRING NOT NULL COMMENT 'Type of entity: catalog, schema, table, or column',
    entity_catalog STRING NOT NULL COMMENT 'Catalog name',
    entity_schema STRING COMMENT 'Schema name (if applicable)',
    entity_table STRING COMMENT 'Table name (if applicable)',
    entity_column STRING COMMENT 'Column name (if applicable)',
    entity_full_path STRING NOT NULL COMMENT 'Full path to the entity',
    current_comment STRING COMMENT 'Existing comment on the entity',
    suggested_comment STRING NOT NULL COMMENT 'Proposed new comment',
    status STRING NOT NULL COMMENT 'Current status: draft, pending, approved, rejected, or applied',
    created_by STRING NOT NULL COMMENT 'User ID who created the suggestion',
    approved_by STRING COMMENT 'User ID who approved (if applicable)',
    submitted_at TIMESTAMP COMMENT 'When submitted for approval',
    approved_at TIMESTAMP COMMENT 'When approved',
    applied_at TIMESTAMP COMMENT 'When applied to the entity',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Creation timestamp',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'Last update timestamp',
    CONSTRAINT pk_suggestions PRIMARY KEY(suggestion_id)
)
USING DELTA
PARTITIONED BY (status, entity_type)
COMMENT 'Central repository tracking all metadata comment suggestions and their lifecycle';

-- Create approvals table
CREATE TABLE IF NOT EXISTS approvals (
    approval_id STRING NOT NULL COMMENT 'Unique identifier for the approval action',
    suggestion_id STRING NOT NULL COMMENT 'Related suggestion ID',
    approver_id STRING NOT NULL COMMENT 'User ID of the approver',
    action STRING NOT NULL COMMENT 'Action taken: approved, rejected, or request_changes',
    feedback STRING COMMENT 'Feedback provided by the approver',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'When the approval action was taken',
    CONSTRAINT pk_approvals PRIMARY KEY(approval_id)
)
USING DELTA
COMMENT 'Complete history of all approval actions on comment suggestions';

-- Create audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id STRING NOT NULL COMMENT 'Unique identifier for the log entry',
    user_id STRING COMMENT 'User who performed the action',
    username STRING COMMENT 'Username for quick reference',
    action STRING NOT NULL COMMENT 'Action performed',
    entity_type STRING COMMENT 'Type of entity affected',
    entity_id STRING COMMENT 'ID of the entity affected',
    entity_path STRING COMMENT 'Full path to the entity',
    details STRING COMMENT 'JSON string with additional context',
    ip_address STRING COMMENT 'IP address of the user',
    user_agent STRING COMMENT 'Browser/client information',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'When the action occurred',
    CONSTRAINT pk_audit_logs PRIMARY KEY(log_id)
)
USING DELTA
PARTITIONED BY (DATE(created_at))
COMMENT 'Comprehensive audit trail for all system activities and changes';

-- Insert sample users
INSERT INTO users (user_id, username, email, full_name, role) VALUES
    ('u001', 'john_suggest', 'john.suggest@example.com', 'John Doe', 'suggest_only'),
    ('u002', 'jane_approver', 'jane.approver@example.com', 'Jane Smith', 'approver'),
    ('u003', 'admin_user', 'admin@example.com', 'Admin User', 'admin'),
    ('u004', 'alice_suggest', 'alice.suggest@example.com', 'Alice Johnson', 'suggest_only'),
    ('u005', 'bob_approver', 'bob.approver@example.com', 'Bob Williams', 'approver');

-- Create useful views
CREATE OR REPLACE VIEW v_pending_approvals AS
SELECT 
    cs.suggestion_id,
    cs.entity_type,
    cs.entity_full_path,
    cs.current_comment,
    cs.suggested_comment,
    cs.created_by,
    u.username as created_by_name,
    u.full_name as created_by_full_name,
    cs.submitted_at,
    DATEDIFF(CURRENT_TIMESTAMP(), cs.submitted_at) as days_pending
FROM comment_suggestions cs
JOIN users u ON cs.created_by = u.user_id
WHERE cs.status = 'pending'
ORDER BY cs.submitted_at;

-- Create user activity view
CREATE OR REPLACE VIEW v_user_activity AS
SELECT 
    u.user_id,
    u.username,
    u.full_name,
    u.role,
    COUNT(DISTINCT cs.suggestion_id) as total_suggestions,
    COUNT(DISTINCT CASE WHEN cs.status = 'draft' THEN cs.suggestion_id END) as draft_count,
    COUNT(DISTINCT CASE WHEN cs.status = 'pending' THEN cs.suggestion_id END) as pending_count,
    COUNT(DISTINCT CASE WHEN cs.status = 'approved' THEN cs.suggestion_id END) as approved_count,
    COUNT(DISTINCT CASE WHEN cs.status = 'rejected' THEN cs.suggestion_id END) as rejected_count,
    COUNT(DISTINCT a.approval_id) as approvals_given
FROM users u
LEFT JOIN comment_suggestions cs ON u.user_id = cs.created_by
LEFT JOIN approvals a ON u.user_id = a.approver_id
GROUP BY u.user_id, u.username, u.full_name, u.role;

-- Verify the setup
SELECT 'Schema Created Successfully!' as status;
SELECT COUNT(*) as user_count FROM users;
SHOW TABLES IN arao.metadata_manager;
```

4. **Execute the script**: Run the entire SQL script in your Databricks workspace.

## Option 2: Using Python Script with Token

If you prefer to use the Python script:

1. **Get your Databricks access token**:
   - In your Databricks workspace, go to Settings → Developer → Personal Access Tokens
   - Create a new token
   - Copy the token

2. **Set the environment variable**:
```bash
export DATABRICKS_TOKEN='your-token-here'
```

3. **Run the Python script**:
```bash
source venv/bin/activate
python databricks/run_schema_setup.py
```

## Verification

After running either option, verify the schema was created:

```sql
USE CATALOG arao;
SHOW SCHEMAS;
SELECT * FROM metadata_manager.users;
```

You should see the `metadata_manager` schema and 5 test users in the users table.

## Next Steps

Once the schema is created:

1. **Update backend configuration**: Make sure your FastAPI backend has the correct Databricks credentials
2. **Start the backend**: The backend can now connect to your Databricks workspace
3. **Test the application**: Try logging in with the test users through the frontend

The frontend is already running at: http://localhost:4001