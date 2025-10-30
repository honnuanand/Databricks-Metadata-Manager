#!/usr/bin/env python3
"""
Execute the Databricks schema setup for Metadata Manager
This script connects to your Databricks workspace and creates the necessary schema and tables.
"""

import os
import sys
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import DatabricksError
import time

def get_databricks_client():
    """Initialize Databricks client with credentials from environment or config."""
    try:
        # Try to get credentials from environment variables
        host = os.getenv("DATABRICKS_HOST", "https://e2-demo-field-eng.cloud.databricks.com")
        token = os.getenv("DATABRICKS_TOKEN")
        
        if not token:
            print("Error: DATABRICKS_TOKEN environment variable not set")
            print("Please set your Databricks token:")
            print("export DATABRICKS_TOKEN='your-token-here'")
            return None
        
        client = WorkspaceClient(host=host, token=token)
        print(f"✅ Connected to Databricks workspace: {host}")
        return client
        
    except Exception as e:
        print(f"❌ Failed to connect to Databricks: {e}")
        return None

def execute_sql_statement(client, sql, description=""):
    """Execute a SQL statement and handle errors."""
    try:
        print(f"🔄 {description}...")
        
        # Use SQL execution API
        with client.sql.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
        
        print(f"✅ {description} - Success")
        return True
        
    except DatabricksError as e:
        print(f"⚠️  {description} - Warning: {e}")
        # Some operations might fail if they already exist, which is okay
        return False
    except Exception as e:
        print(f"❌ {description} - Error: {e}")
        return False

def main():
    """Main execution function."""
    print("🚀 Databricks Metadata Manager Schema Setup")
    print("=" * 50)
    
    # Get Databricks client
    client = get_databricks_client()
    if not client:
        sys.exit(1)
    
    # Test connection
    try:
        current_user = client.current_user.me()
        print(f"✅ Authenticated as: {current_user.user_name}")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("Creating Schema and Tables...")
    print("=" * 50)
    
    # SQL statements to execute
    sql_statements = [
        # 1. Create schema
        {
            "sql": """
            CREATE SCHEMA IF NOT EXISTS arao.metadata_manager
            COMMENT 'Central repository for Databricks metadata management - tracks comment suggestions, approvals, and comprehensive audit logs'
            """,
            "description": "Creating metadata_manager schema"
        },
        
        # 2. Use schema
        {
            "sql": "USE CATALOG arao",
            "description": "Setting catalog to arao"
        },
        
        {
            "sql": "USE SCHEMA metadata_manager",
            "description": "Setting schema to metadata_manager"
        },
        
        # 3. Create users table
        {
            "sql": """
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
            COMMENT 'System users with role-based access for metadata management'
            """,
            "description": "Creating users table"
        },
        
        # 4. Create comment suggestions table
        {
            "sql": """
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
            COMMENT 'Central repository tracking all metadata comment suggestions and their lifecycle'
            """,
            "description": "Creating comment_suggestions table"
        },
        
        # 5. Create approvals table
        {
            "sql": """
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
            COMMENT 'Complete history of all approval actions on comment suggestions'
            """,
            "description": "Creating approvals table"
        },
        
        # 6. Create audit logs table
        {
            "sql": """
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
            COMMENT 'Comprehensive audit trail for all system activities and changes'
            """,
            "description": "Creating audit_logs table"
        },
        
        # 7. Insert sample users
        {
            "sql": """
            INSERT INTO users (user_id, username, email, full_name, role) VALUES
                ('u001', 'john_suggest', 'john.suggest@example.com', 'John Doe', 'suggest_only'),
                ('u002', 'jane_approver', 'jane.approver@example.com', 'Jane Smith', 'approver'),
                ('u003', 'admin_user', 'admin@example.com', 'Admin User', 'admin'),
                ('u004', 'alice_suggest', 'alice.suggest@example.com', 'Alice Johnson', 'suggest_only'),
                ('u005', 'bob_approver', 'bob.approver@example.com', 'Bob Williams', 'approver')
            """,
            "description": "Inserting sample users"
        }
    ]
    
    # Execute all SQL statements
    success_count = 0
    for stmt in sql_statements:
        if execute_sql_statement(client, stmt["sql"], stmt["description"]):
            success_count += 1
        time.sleep(1)  # Brief pause between operations
    
    print("\n" + "=" * 50)
    print("Creating Views...")
    print("=" * 50)
    
    # Create views
    view_statements = [
        {
            "sql": """
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
            ORDER BY cs.submitted_at
            """,
            "description": "Creating v_pending_approvals view"
        },
        
        {
            "sql": """
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
            GROUP BY u.user_id, u.username, u.full_name, u.role
            """,
            "description": "Creating v_user_activity view"
        }
    ]
    
    for stmt in view_statements:
        if execute_sql_statement(client, stmt["sql"], stmt["description"]):
            success_count += 1
    
    print("\n" + "=" * 50)
    print("Setup Complete!")
    print("=" * 50)
    
    print(f"✅ Successfully executed {success_count}/{len(sql_statements) + len(view_statements)} statements")
    
    # Verify setup
    try:
        with client.sql.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as user_count FROM arao.metadata_manager.users")
                result = cursor.fetchone()
                user_count = result[0] if result else 0
                print(f"✅ Verified: {user_count} users in the database")
    except Exception as e:
        print(f"⚠️  Could not verify setup: {e}")
    
    print("\n🎉 Your Databricks Metadata Manager schema is ready!")
    print("📊 You can now query: SELECT * FROM arao.metadata_manager.users")
    print("🔗 Access your workspace at: https://e2-demo-field-eng.cloud.databricks.com")

if __name__ == "__main__":
    main()