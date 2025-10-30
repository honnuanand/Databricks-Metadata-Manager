#!/usr/bin/env python3
"""
Create Databricks Metadata Manager Schema using databricks.sql like the tariff project
"""

import os
import sys
from databricks import sql
import time

def main():
    """Create the schema using the same approach as the tariff tracker project."""
    
    print("🚀 Databricks Metadata Manager Schema Creation")
    print("=" * 60)
    
    import os
    # Connection parameters (same pattern as tariff project)
    connection_params = {
        "server_hostname": "e2-demo-field-eng.cloud.databricks.com",
        "http_path": "/sql/1.0/warehouses/00887ae543d50e2a",  # Using same warehouse as tariff project
        "access_token": os.environ["DATABRICKS_TOKEN"]  # From environment variable
    }
    
    # SQL commands to execute
    sql_commands = [
        "CREATE SCHEMA IF NOT EXISTS arao.metadata_manager COMMENT 'Central repository for Databricks metadata management'",
        
        """CREATE TABLE IF NOT EXISTS arao.metadata_manager.users (
            user_id STRING NOT NULL,
            username STRING NOT NULL,
            email STRING NOT NULL,
            full_name STRING,
            role STRING NOT NULL,
            is_active BOOLEAN,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        ) USING DELTA
        COMMENT 'System users with role-based access for metadata management'""",
        
        """CREATE TABLE IF NOT EXISTS arao.metadata_manager.comment_suggestions (
            suggestion_id STRING NOT NULL,
            entity_type STRING NOT NULL,
            entity_catalog STRING NOT NULL,
            entity_schema STRING,
            entity_table STRING,
            entity_column STRING,
            entity_full_path STRING NOT NULL,
            current_comment STRING,
            suggested_comment STRING NOT NULL,
            status STRING NOT NULL,
            created_by STRING NOT NULL,
            approved_by STRING,
            submitted_at TIMESTAMP,
            approved_at TIMESTAMP,
            applied_at TIMESTAMP,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        ) USING DELTA
        COMMENT 'Central repository tracking all metadata comment suggestions'""",
        
        """CREATE TABLE IF NOT EXISTS arao.metadata_manager.approvals (
            approval_id STRING NOT NULL,
            suggestion_id STRING NOT NULL,
            approver_id STRING NOT NULL,
            action STRING NOT NULL,
            feedback STRING,
            created_at TIMESTAMP
        ) USING DELTA
        COMMENT 'Complete history of all approval actions on comment suggestions'""",
        
        """CREATE TABLE IF NOT EXISTS arao.metadata_manager.audit_logs (
            log_id STRING NOT NULL,
            user_id STRING,
            username STRING,
            action STRING NOT NULL,
            entity_type STRING,
            entity_id STRING,
            entity_path STRING,
            details STRING,
            ip_address STRING,
            user_agent STRING,
            created_at TIMESTAMP
        ) USING DELTA
        COMMENT 'Comprehensive audit trail for all system activities'""",
        
        """INSERT INTO arao.metadata_manager.users (user_id, username, email, full_name, role, is_active, created_at, updated_at) VALUES
            ('u001', 'john_suggest', 'john.suggest@example.com', 'John Doe', 'suggest_only', true, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
            ('u002', 'jane_approver', 'jane.approver@example.com', 'Jane Smith', 'approver', true, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
            ('u003', 'admin_user', 'admin@example.com', 'Admin User', 'admin', true, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
            ('u004', 'alice_suggest', 'alice.suggest@example.com', 'Alice Johnson', 'suggest_only', true, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()),
            ('u005', 'bob_approver', 'bob.approver@example.com', 'Bob Williams', 'approver', true, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP())""",
        
        """CREATE OR REPLACE VIEW arao.metadata_manager.v_user_activity AS
        SELECT 
            u.user_id,
            u.username,
            u.full_name,
            u.role,
            COUNT(DISTINCT cs.suggestion_id) as total_suggestions,
            COUNT(DISTINCT CASE WHEN cs.status = 'draft' THEN cs.suggestion_id END) as draft_count,
            COUNT(DISTINCT CASE WHEN cs.status = 'pending' THEN cs.suggestion_id END) as pending_count,
            COUNT(DISTINCT CASE WHEN cs.status = 'approved' THEN cs.suggestion_id END) as approved_count,
            COUNT(DISTINCT a.approval_id) as approvals_given
        FROM arao.metadata_manager.users u
        LEFT JOIN arao.metadata_manager.comment_suggestions cs ON u.user_id = cs.created_by
        LEFT JOIN arao.metadata_manager.approvals a ON u.user_id = a.approver_id
        GROUP BY u.user_id, u.username, u.full_name, u.role"""
    ]
    
    try:
        # Connect to Databricks (same pattern as tariff project)
        print("🔌 Connecting to Databricks...")
        connection = sql.connect(**connection_params)
        cursor = connection.cursor()
        print("✅ Connected successfully!")
        
        # Execute each SQL command
        success_count = 0
        for i, command in enumerate(sql_commands, 1):
            try:
                print(f"🔄 Executing step {i}/{len(sql_commands)}...")
                cursor.execute(command)
                print(f"✅ Step {i} completed successfully")
                success_count += 1
                time.sleep(0.5)  # Brief pause between commands
                
            except Exception as e:
                error_str = str(e).lower()
                if "already exists" in error_str or "duplicate" in error_str:
                    print(f"✅ Step {i} - Already exists (OK)")
                    success_count += 1
                else:
                    print(f"❌ Step {i} failed: {e}")
        
        print("\n" + "=" * 60)
        print("🎯 Verification")
        print("=" * 60)
        
        # Verify the setup by counting users
        try:
            cursor.execute("SELECT COUNT(*) FROM arao.metadata_manager.users")
            result = cursor.fetchone()
            user_count = result[0] if result else 0
            print(f"✅ Found {user_count} users in the database")
            
            # Show the users
            cursor.execute("SELECT username, role FROM arao.metadata_manager.users ORDER BY username")
            users = cursor.fetchall()
            print("\n👥 Created Users:")
            for username, role in users:
                print(f"   • {username} ({role})")
                
        except Exception as e:
            print(f"⚠️  Could not verify setup: {e}")
        
        print("\n" + "=" * 60)
        print("🎉 Setup Complete!")
        print("=" * 60)
        print(f"✅ Successfully executed {success_count}/{len(sql_commands)} commands")
        print(f"📊 Schema: arao.metadata_manager")
        print(f"🔗 Workspace: https://e2-demo-field-eng.cloud.databricks.com")
        
        print("\n🔍 Test Queries:")
        print("   SELECT * FROM arao.metadata_manager.users;")
        print("   SELECT * FROM arao.metadata_manager.v_user_activity;")
        print("   SHOW TABLES IN arao.metadata_manager;")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check your Databricks token")
        print("   2. Verify warehouse is running")
        print("   3. Ensure you have CREATE privileges on the arao catalog")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)