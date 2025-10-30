-- ============================================================
-- Databricks Metadata Manager Schema Setup
-- Catalog: arao
-- Schema: metadata_manager
-- Workspace: https://e2-demo-field-eng.cloud.databricks.com/
-- ============================================================

-- Create the metadata management schema
CREATE SCHEMA IF NOT EXISTS arao.metadata_manager
COMMENT 'Central repository for Databricks metadata management - tracks comment suggestions, approvals, and comprehensive audit logs';

-- Set the current schema
USE CATALOG arao;
USE SCHEMA metadata_manager;

-- ============================================================
-- Core Tables
-- ============================================================

-- 1. Users table - Track users and their roles
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
TBLPROPERTIES (
    'delta.minReaderVersion' = '1',
    'delta.minWriterVersion' = '2'
)
COMMENT 'System users with role-based access for metadata management';

-- 2. Comment suggestions table - Core table for tracking all suggestions
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
TBLPROPERTIES (
    'delta.autoOptimize.optimizeWrite' = 'true',
    'delta.autoOptimize.autoCompact' = 'true'
)
COMMENT 'Central repository tracking all metadata comment suggestions and their lifecycle';

-- 3. Approvals table - Track approval actions
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

-- 4. Comprehensive audit log
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
TBLPROPERTIES (
    'delta.logRetentionDuration' = 'interval 90 days'
)
COMMENT 'Comprehensive audit trail for all system activities and changes';

-- 5. Applied comments history
CREATE TABLE IF NOT EXISTS applied_comments (
    applied_id STRING NOT NULL COMMENT 'Unique identifier for the applied change',
    suggestion_id STRING NOT NULL COMMENT 'Original suggestion ID',
    entity_type STRING NOT NULL COMMENT 'Type of entity',
    entity_full_path STRING NOT NULL COMMENT 'Full path to the entity',
    previous_comment STRING COMMENT 'Previous comment value',
    new_comment STRING NOT NULL COMMENT 'New comment value',
    applied_by STRING NOT NULL COMMENT 'User who applied the change',
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'When the change was applied',
    rollback_at TIMESTAMP COMMENT 'If rolled back, when',
    rollback_by STRING COMMENT 'If rolled back, by whom',
    CONSTRAINT pk_applied PRIMARY KEY(applied_id)
)
USING DELTA
COMMENT 'Historical record of all successfully applied metadata changes with rollback capability';

-- 6. Daily statistics table
CREATE TABLE IF NOT EXISTS metadata_statistics (
    stat_date DATE NOT NULL COMMENT 'Date for the statistics',
    total_suggestions BIGINT COMMENT 'Total suggestions created',
    pending_approvals BIGINT COMMENT 'Number of pending approvals',
    approved_count BIGINT COMMENT 'Number approved',
    rejected_count BIGINT COMMENT 'Number rejected',
    applied_count BIGINT COMMENT 'Number successfully applied',
    active_users BIGINT COMMENT 'Number of active users',
    catalog_coverage_percent DECIMAL(5,2) COMMENT 'Percentage of catalogs with comments',
    schema_coverage_percent DECIMAL(5,2) COMMENT 'Percentage of schemas with comments',
    table_coverage_percent DECIMAL(5,2) COMMENT 'Percentage of tables with comments',
    column_coverage_percent DECIMAL(5,2) COMMENT 'Percentage of columns with comments',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP() COMMENT 'When statistics were calculated',
    CONSTRAINT pk_stats PRIMARY KEY(stat_date)
)
USING DELTA
COMMENT 'Aggregated daily statistics for tracking metadata coverage and system usage';

-- ============================================================
-- Views for Common Queries
-- ============================================================

-- Pending approvals with user details
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

-- User activity summary
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

-- Entity coverage report
CREATE OR REPLACE VIEW v_entity_coverage AS
SELECT 
    entity_type,
    entity_catalog,
    COUNT(DISTINCT entity_full_path) as total_entities,
    COUNT(DISTINCT CASE WHEN current_comment IS NOT NULL THEN entity_full_path END) as entities_with_comments,
    COUNT(DISTINCT CASE WHEN status = 'pending' THEN entity_full_path END) as pending_updates,
    COUNT(DISTINCT CASE WHEN status = 'applied' AND applied_at >= CURRENT_DATE() - INTERVAL 30 DAYS THEN entity_full_path END) as recently_updated
FROM comment_suggestions
GROUP BY entity_type, entity_catalog
ORDER BY entity_catalog, entity_type;

-- Recent activity view
CREATE OR REPLACE VIEW v_recent_activity AS
SELECT 
    'suggestion' as activity_type,
    cs.suggestion_id as activity_id,
    cs.created_by as user_id,
    u.username,
    cs.entity_full_path,
    cs.created_at as activity_time,
    cs.status
FROM comment_suggestions cs
JOIN users u ON cs.created_by = u.user_id
WHERE cs.created_at >= CURRENT_DATE() - INTERVAL 7 DAYS

UNION ALL

SELECT 
    'approval' as activity_type,
    a.approval_id as activity_id,
    a.approver_id as user_id,
    u.username,
    cs.entity_full_path,
    a.created_at as activity_time,
    a.action as status
FROM approvals a
JOIN users u ON a.approver_id = u.user_id
JOIN comment_suggestions cs ON a.suggestion_id = cs.suggestion_id
WHERE a.created_at >= CURRENT_DATE() - INTERVAL 7 DAYS

ORDER BY activity_time DESC;

-- ============================================================
-- Insert Initial Test Data
-- ============================================================

-- Insert test users
INSERT INTO users (user_id, username, email, full_name, role) VALUES
    ('u001', 'john_suggest', 'john.suggest@example.com', 'John Doe', 'suggest_only'),
    ('u002', 'jane_approver', 'jane.approver@example.com', 'Jane Smith', 'approver'),
    ('u003', 'admin_user', 'admin@example.com', 'Admin User', 'admin'),
    ('u004', 'alice_suggest', 'alice.suggest@example.com', 'Alice Johnson', 'suggest_only'),
    ('u005', 'bob_approver', 'bob.approver@example.com', 'Bob Williams', 'approver');

-- Insert sample suggestion for the metadata_manager schema itself
INSERT INTO comment_suggestions (
    suggestion_id,
    entity_type,
    entity_catalog,
    entity_schema,
    entity_full_path,
    current_comment,
    suggested_comment,
    status,
    created_by
) VALUES (
    'cs001',
    'schema',
    'arao',
    'metadata_manager',
    'arao.metadata_manager',
    'Central repository for Databricks metadata management - tracks comment suggestions, approvals, and comprehensive audit logs',
    'Comprehensive metadata management system for Databricks catalogs. Enables collaborative documentation through suggestion and approval workflows, maintains complete audit trails, and tracks metadata coverage metrics across all catalog entities.',
    'draft',
    'u001'
);

-- ============================================================
-- Useful Queries for Operations
-- ============================================================

-- Check the schema is created successfully
SELECT 
    catalog_name,
    schema_name,
    comment,
    owner,
    created
FROM information_schema.schemata
WHERE catalog_name = 'arao' 
  AND schema_name = 'metadata_manager';

-- View all tables in the schema
SHOW TABLES IN arao.metadata_manager;

-- Check pending approvals
SELECT * FROM arao.metadata_manager.v_pending_approvals;

-- Check user activity
SELECT * FROM arao.metadata_manager.v_user_activity;

-- View recent activity
SELECT * FROM arao.metadata_manager.v_recent_activity;