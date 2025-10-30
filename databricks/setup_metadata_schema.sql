-- Databricks SQL Script to create Metadata Manager Schema
-- This creates a dedicated schema to track all metadata management activities

-- Create the metadata management schema
CREATE SCHEMA IF NOT EXISTS arao.metadata_manager
COMMENT 'Schema for Databricks Metadata Manager application - tracks comment suggestions, approvals, and audit logs';

-- Use the schema
USE arao.metadata_manager;

-- 1. Users table for tracking who makes suggestions and approvals
CREATE TABLE IF NOT EXISTS users (
    user_id STRING NOT NULL,
    username STRING NOT NULL,
    email STRING NOT NULL,
    full_name STRING,
    role STRING NOT NULL, -- 'suggest_only', 'approver', 'admin'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT pk_users PRIMARY KEY(user_id)
)
USING DELTA
COMMENT 'Users who interact with the metadata management system';

-- 2. Comment suggestions table
CREATE TABLE IF NOT EXISTS comment_suggestions (
    suggestion_id STRING NOT NULL,
    entity_type STRING NOT NULL, -- 'catalog', 'schema', 'table', 'column'
    entity_catalog STRING NOT NULL,
    entity_schema STRING,
    entity_table STRING,
    entity_column STRING,
    entity_full_path STRING NOT NULL,
    current_comment STRING,
    suggested_comment STRING NOT NULL,
    status STRING NOT NULL, -- 'draft', 'pending', 'approved', 'rejected', 'applied'
    created_by STRING NOT NULL,
    approved_by STRING,
    submitted_at TIMESTAMP,
    approved_at TIMESTAMP,
    applied_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT pk_suggestions PRIMARY KEY(suggestion_id)
)
USING DELTA
PARTITIONED BY (status, entity_type)
COMMENT 'Tracks all comment suggestions for catalog entities';

-- 3. Approvals table for tracking approval actions
CREATE TABLE IF NOT EXISTS approvals (
    approval_id STRING NOT NULL,
    suggestion_id STRING NOT NULL,
    approver_id STRING NOT NULL,
    action STRING NOT NULL, -- 'approved', 'rejected', 'request_changes'
    feedback STRING,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT pk_approvals PRIMARY KEY(approval_id)
)
USING DELTA
COMMENT 'Approval history for comment suggestions';

-- 4. Audit log table for tracking all actions
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id STRING NOT NULL,
    user_id STRING,
    username STRING,
    action STRING NOT NULL,
    entity_type STRING,
    entity_id STRING,
    entity_path STRING,
    details STRING, -- JSON string with additional details
    ip_address STRING,
    user_agent STRING,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT pk_audit_logs PRIMARY KEY(log_id)
)
USING DELTA
PARTITIONED BY (DATE(created_at))
COMMENT 'Comprehensive audit trail of all system actions';

-- 5. Applied comments table - tracks what comments have been successfully applied
CREATE TABLE IF NOT EXISTS applied_comments (
    applied_id STRING NOT NULL,
    suggestion_id STRING NOT NULL,
    entity_type STRING NOT NULL,
    entity_full_path STRING NOT NULL,
    previous_comment STRING,
    new_comment STRING NOT NULL,
    applied_by STRING NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    rollback_at TIMESTAMP,
    rollback_by STRING,
    CONSTRAINT pk_applied PRIMARY KEY(applied_id)
)
USING DELTA
COMMENT 'History of successfully applied comment changes';

-- 6. Metadata statistics table for tracking metrics
CREATE TABLE IF NOT EXISTS metadata_statistics (
    stat_date DATE NOT NULL,
    total_suggestions BIGINT,
    pending_approvals BIGINT,
    approved_count BIGINT,
    rejected_count BIGINT,
    applied_count BIGINT,
    active_users BIGINT,
    catalog_coverage_percent DECIMAL(5,2),
    schema_coverage_percent DECIMAL(5,2),
    table_coverage_percent DECIMAL(5,2),
    column_coverage_percent DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT pk_stats PRIMARY KEY(stat_date)
)
USING DELTA
COMMENT 'Daily statistics for metadata management metrics';

-- Create views for common queries

-- View: Pending approvals with full details
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

-- View: User activity summary
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

-- View: Entity coverage report
CREATE OR REPLACE VIEW v_entity_coverage AS
SELECT 
    entity_type,
    entity_catalog,
    COUNT(DISTINCT entity_full_path) as total_entities,
    COUNT(DISTINCT CASE WHEN current_comment IS NOT NULL THEN entity_full_path END) as entities_with_comments,
    COUNT(DISTINCT CASE WHEN status = 'pending' THEN entity_full_path END) as pending_updates,
    COUNT(DISTINCT CASE WHEN status = 'applied' THEN entity_full_path END) as recently_updated
FROM comment_suggestions
GROUP BY entity_type, entity_catalog
ORDER BY entity_catalog, entity_type;

-- Insert sample test users
INSERT INTO users (user_id, username, email, full_name, role) VALUES
    ('u001', 'john_suggest', 'john.suggest@example.com', 'John Doe', 'suggest_only'),
    ('u002', 'jane_approver', 'jane.approver@example.com', 'Jane Smith', 'approver'),
    ('u003', 'admin_user', 'admin@example.com', 'Admin User', 'admin'),
    ('u004', 'alice_suggest', 'alice.suggest@example.com', 'Alice Johnson', 'suggest_only'),
    ('u005', 'bob_approver', 'bob.approver@example.com', 'Bob Williams', 'approver');

-- Sample comment suggestion
INSERT INTO comment_suggestions (
    suggestion_id,
    entity_type,
    entity_catalog,
    entity_schema,
    entity_table,
    entity_full_path,
    current_comment,
    suggested_comment,
    status,
    created_by
) VALUES (
    'cs001',
    'table',
    'arao',
    'metadata_manager',
    'comment_suggestions',
    'arao.metadata_manager.comment_suggestions',
    'Tracks all comment suggestions for catalog entities',
    'Central table for tracking all metadata comment suggestions submitted by users for review and approval',
    'draft',
    'u001'
);

-- Grant appropriate permissions (adjust based on your setup)
-- GRANT SELECT ON SCHEMA arao.metadata_manager TO `metadata_readers`;
-- GRANT ALL PRIVILEGES ON SCHEMA arao.metadata_manager TO `metadata_admins`;

-- Create a stored procedure for applying approved comments
-- Note: This is pseudo-code as Databricks SQL doesn't support full stored procedures yet
-- You would implement this logic in your application code
/*
CREATE OR REPLACE FUNCTION apply_approved_comment(
    p_suggestion_id STRING,
    p_approver_id STRING
) RETURNS STRING
AS
BEGIN
    -- 1. Get the suggestion details
    -- 2. Build and execute the ALTER TABLE/COMMENT statement
    -- 3. Update the suggestion status to 'applied'
    -- 4. Insert into applied_comments table
    -- 5. Insert audit log entry
    -- 6. Return success/failure message
END;
*/

-- Useful queries for monitoring

-- Check pending approvals count by catalog
SELECT 
    entity_catalog,
    COUNT(*) as pending_count
FROM comment_suggestions
WHERE status = 'pending'
GROUP BY entity_catalog
ORDER BY pending_count DESC;

-- Recent activity (last 7 days)
SELECT 
    DATE(created_at) as activity_date,
    COUNT(DISTINCT CASE WHEN action = 'suggestion_created' THEN entity_id END) as new_suggestions,
    COUNT(DISTINCT CASE WHEN action = 'suggestion_approved' THEN entity_id END) as approvals,
    COUNT(DISTINCT CASE WHEN action = 'suggestion_rejected' THEN entity_id END) as rejections
FROM audit_logs
WHERE created_at >= CURRENT_DATE() - INTERVAL 7 DAYS
GROUP BY DATE(created_at)
ORDER BY activity_date DESC;