#!/usr/bin/env python3
"""
Initialize Databricks schema for Metadata Manager application
This script creates the metadata_manager schema and all necessary tables
"""

import os
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import sql
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabricksSchemaInitializer:
    def __init__(self, host: str, token: str):
        """Initialize Databricks client."""
        self.client = WorkspaceClient(host=host, token=token)
        self.catalog = "arao"  # Your Databricks catalog name
        self.schema_name = "metadata_manager"
        
    def create_schema(self):
        """Create the metadata_manager schema."""
        sql_statement = f"""
        CREATE SCHEMA IF NOT EXISTS {self.catalog}.{self.schema_name}
        COMMENT 'Metadata Manager - Central repository for tracking comment suggestions, approvals, and audit logs for Databricks catalog entities'
        """
        
        try:
            with self.client.sql.connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql_statement)
            logger.info(f"Schema {self.catalog}.{self.schema_name} created successfully")
        except Exception as e:
            logger.error(f"Error creating schema: {e}")
            raise
    
    def create_tables(self):
        """Create all necessary tables for the metadata manager."""
        tables_sql = [
            # Users table
            f"""
            CREATE TABLE IF NOT EXISTS {self.catalog}.{self.schema_name}.users (
                user_id STRING NOT NULL,
                username STRING NOT NULL,
                email STRING NOT NULL,
                full_name STRING,
                role STRING NOT NULL COMMENT 'User role: suggest_only, approver, or admin',
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                CONSTRAINT pk_users PRIMARY KEY(user_id)
            )
            USING DELTA
            COMMENT 'System users with different permission levels for metadata management'
            """,
            
            # Comment suggestions table
            f"""
            CREATE TABLE IF NOT EXISTS {self.catalog}.{self.schema_name}.comment_suggestions (
                suggestion_id STRING NOT NULL,
                entity_type STRING NOT NULL COMMENT 'Type: catalog, schema, table, or column',
                entity_catalog STRING NOT NULL,
                entity_schema STRING,
                entity_table STRING,
                entity_column STRING,
                entity_full_path STRING NOT NULL,
                current_comment STRING,
                suggested_comment STRING NOT NULL,
                status STRING NOT NULL COMMENT 'Status: draft, pending, approved, rejected, or applied',
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
            COMMENT 'Central repository for all metadata comment suggestions'
            """,
            
            # Approvals table
            f"""
            CREATE TABLE IF NOT EXISTS {self.catalog}.{self.schema_name}.approvals (
                approval_id STRING NOT NULL,
                suggestion_id STRING NOT NULL,
                approver_id STRING NOT NULL,
                action STRING NOT NULL COMMENT 'Action taken: approved, rejected, or request_changes',
                feedback STRING,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                CONSTRAINT pk_approvals PRIMARY KEY(approval_id)
            )
            USING DELTA
            COMMENT 'Approval workflow history for comment suggestions'
            """,
            
            # Audit logs table
            f"""
            CREATE TABLE IF NOT EXISTS {self.catalog}.{self.schema_name}.audit_logs (
                log_id STRING NOT NULL,
                user_id STRING,
                username STRING,
                action STRING NOT NULL,
                entity_type STRING,
                entity_id STRING,
                entity_path STRING,
                details STRING COMMENT 'JSON string with additional context',
                ip_address STRING,
                user_agent STRING,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
                CONSTRAINT pk_audit_logs PRIMARY KEY(log_id)
            )
            USING DELTA
            PARTITIONED BY (DATE(created_at))
            COMMENT 'Comprehensive audit trail for all metadata management activities'
            """,
            
            # Applied comments history
            f"""
            CREATE TABLE IF NOT EXISTS {self.catalog}.{self.schema_name}.applied_comments (
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
            COMMENT 'Historical record of all successfully applied metadata changes'
            """,
            
            # Metadata coverage statistics
            f"""
            CREATE TABLE IF NOT EXISTS {self.catalog}.{self.schema_name}.metadata_statistics (
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
            COMMENT 'Daily aggregated statistics for metadata coverage and activity metrics'
            """
        ]
        
        for sql in tables_sql:
            try:
                with self.client.sql.connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(sql)
                logger.info("Table created successfully")
            except Exception as e:
                logger.error(f"Error creating table: {e}")
    
    def create_views(self):
        """Create useful views for querying."""
        views_sql = [
            # Pending approvals view
            f"""
            CREATE OR REPLACE VIEW {self.catalog}.{self.schema_name}.v_pending_approvals AS
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
            FROM {self.catalog}.{self.schema_name}.comment_suggestions cs
            JOIN {self.catalog}.{self.schema_name}.users u ON cs.created_by = u.user_id
            WHERE cs.status = 'pending'
            ORDER BY cs.submitted_at
            """,
            
            # User activity summary
            f"""
            CREATE OR REPLACE VIEW {self.catalog}.{self.schema_name}.v_user_activity AS
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
            FROM {self.catalog}.{self.schema_name}.users u
            LEFT JOIN {self.catalog}.{self.schema_name}.comment_suggestions cs ON u.user_id = cs.created_by
            LEFT JOIN {self.catalog}.{self.schema_name}.approvals a ON u.user_id = a.approver_id
            GROUP BY u.user_id, u.username, u.full_name, u.role
            """,
            
            # Coverage report view
            f"""
            CREATE OR REPLACE VIEW {self.catalog}.{self.schema_name}.v_coverage_report AS
            SELECT 
                entity_type,
                entity_catalog,
                COUNT(DISTINCT entity_full_path) as total_entities,
                COUNT(DISTINCT CASE WHEN current_comment IS NOT NULL THEN entity_full_path END) as with_comments,
                COUNT(DISTINCT CASE WHEN status = 'pending' THEN entity_full_path END) as pending_updates
            FROM {self.catalog}.{self.schema_name}.comment_suggestions
            GROUP BY entity_type, entity_catalog
            """
        ]
        
        for sql in views_sql:
            try:
                with self.client.sql.connect() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(sql)
                logger.info("View created successfully")
            except Exception as e:
                logger.error(f"Error creating view: {e}")
    
    def insert_sample_data(self):
        """Insert sample test data."""
        # Insert test users
        users_sql = f"""
        INSERT INTO {self.catalog}.{self.schema_name}.users (user_id, username, email, full_name, role)
        VALUES
            ('u001', 'john_suggest', 'john.suggest@example.com', 'John Doe', 'suggest_only'),
            ('u002', 'jane_approver', 'jane.approver@example.com', 'Jane Smith', 'approver'),
            ('u003', 'admin_user', 'admin@example.com', 'Admin User', 'admin')
        """
        
        try:
            with self.client.sql.connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(users_sql)
            logger.info("Sample users inserted successfully")
        except Exception as e:
            logger.warning(f"Sample data may already exist: {e}")
    
    def initialize(self):
        """Run the complete initialization."""
        logger.info(f"Initializing Databricks schema: {self.catalog}.{self.schema_name}")
        
        self.create_schema()
        self.create_tables()
        self.create_views()
        self.insert_sample_data()
        
        logger.info("Databricks schema initialization completed successfully!")
        logger.info(f"Schema: {self.catalog}.{self.schema_name}")
        logger.info("You can now use this schema to track all metadata management activities")


if __name__ == "__main__":
    # Get configuration from environment variables or update these values
    DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "https://e2-demo-field-eng.cloud.databricks.com")
    DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "your-token-here")
    
    # Initialize the schema
    initializer = DatabricksSchemaInitializer(DATABRICKS_HOST, DATABRICKS_TOKEN)
    initializer.initialize()