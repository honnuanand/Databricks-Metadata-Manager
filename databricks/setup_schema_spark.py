#!/usr/bin/env python3
"""
Setup Databricks Metadata Manager Schema using PySpark
This script creates the schema and tables using direct SQL execution like the tariff project
"""

import sys
import os

def create_metadata_schema():
    """Create the metadata manager schema and tables using SQL commands."""
    
    sql_commands = [
        """
        CREATE SCHEMA IF NOT EXISTS arao.metadata_manager
        COMMENT 'Central repository for Databricks metadata management - tracks comment suggestions, approvals, and comprehensive audit logs'
        """,
        
        """
        USE CATALOG arao
        """,
        
        """
        USE SCHEMA metadata_manager
        """,
        
        """
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
        
        """
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
        
        """
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
        
        """
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
        
        """
        MERGE INTO users AS target
        USING (VALUES
            ('u001', 'john_suggest', 'john.suggest@example.com', 'John Doe', 'suggest_only'),
            ('u002', 'jane_approver', 'jane.approver@example.com', 'Jane Smith', 'approver'),
            ('u003', 'admin_user', 'admin@example.com', 'Admin User', 'admin'),
            ('u004', 'alice_suggest', 'alice.suggest@example.com', 'Alice Johnson', 'suggest_only'),
            ('u005', 'bob_approver', 'bob.approver@example.com', 'Bob Williams', 'approver')
        ) AS source(user_id, username, email, full_name, role)
        ON target.user_id = source.user_id
        WHEN NOT MATCHED THEN
            INSERT (user_id, username, email, full_name, role, is_active)
            VALUES (source.user_id, source.username, source.email, source.full_name, source.role, true)
        """,
        
        """
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
        
        """
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
        """
    ]
    
    print("🚀 Databricks Metadata Manager Schema Setup")
    print("=" * 50)
    
    # Execute all SQL commands
    success_count = 0
    for i, sql in enumerate(sql_commands, 1):
        try:
            print(f"🔄 Executing step {i}/{len(sql_commands)}...")
            spark.sql(sql)
            print(f"✅ Step {i} completed successfully")
            success_count += 1
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"✅ Step {i} - Already exists (OK)")
                success_count += 1
            else:
                print(f"❌ Step {i} failed: {e}")
    
    print("\n" + "=" * 50)
    print("Setup Complete!")
    print("=" * 50)
    print(f"✅ Successfully executed {success_count}/{len(sql_commands)} commands")
    
    # Verify setup
    try:
        user_count = spark.sql("SELECT COUNT(*) FROM arao.metadata_manager.users").collect()[0][0]
        print(f"✅ Verified: {user_count} users in the database")
    except Exception as e:
        print(f"⚠️  Could not verify setup: {e}")
    
    print("\n🎉 Your Databricks Metadata Manager schema is ready!")
    print("📊 Schema: arao.metadata_manager")
    print("📋 Tables: users, comment_suggestions, approvals, audit_logs")
    print("📈 Views: v_pending_approvals, v_user_activity")
    print("\n🔍 Test queries:")
    print("   SELECT * FROM arao.metadata_manager.users")
    print("   SELECT * FROM arao.metadata_manager.v_user_activity")
    
    return success_count == len(sql_commands)

if __name__ == "__main__":
    # This script should be run in a Databricks notebook
    print("This script is designed to run in a Databricks notebook environment.")
    print("Copy and paste the SQL commands directly into your Databricks SQL editor instead.")