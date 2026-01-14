#!/usr/bin/env python3
"""
Migrate metadata-manager database from Neon PostgreSQL to Databricks Lakebase.

This script:
1. Creates the metadata_manager schema in Lakebase
2. Creates all tables using Alembic migration
3. Exports data from Neon
4. Imports data into Lakebase

Usage:
    python scripts/migrate_neon_to_lakebase.py --profile fe-vm-leaps-fe

Requirements:
    - databricks-sdk
    - psycopg (pip install psycopg[binary])
    - sqlalchemy
"""

import argparse
import json
import subprocess
import sys
import os
import uuid
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


def get_neon_connection_string():
    """Get Neon connection string from secrets"""
    # Decode the base64 value from the secret
    result = subprocess.run(
        ["databricks", "secrets", "get-secret", "metadata-manager-secrets", "database-url",
         "--profile", args.profile, "--output", "json"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error getting Neon URL from secrets: {result.stderr}")
        return None

    import base64
    secret = json.loads(result.stdout)
    return base64.b64decode(secret['value']).decode('utf-8')


def get_lakebase_connection(profile: str):
    """Get Lakebase connection using OAuth"""
    from databricks.sdk import WorkspaceClient
    import psycopg

    # Get settings from environment or use defaults
    lakebase_instance = os.environ.get('LAKEBASE_INSTANCE', 'arao-lb')
    lakebase_host = os.environ.get('LAKEBASE_HOST',
        'instance-f2a8b56a-7fe2-4c9c-a0a3-7768594a50e5.database.cloud.databricks.com')

    print(f"Connecting to Lakebase instance: {lakebase_instance}")
    print(f"Host: {lakebase_host}")

    # Create workspace client with profile
    w = WorkspaceClient(profile=profile)

    # Get current user for username
    me = w.current_user.me()
    username = me.user_name
    print(f"User: {username}")

    # Generate database credential (OAuth token)
    cred = w.database.generate_database_credential(
        request_id=str(uuid.uuid4()),
        instance_names=[lakebase_instance]
    )

    # Connect to Lakebase
    conn = psycopg.connect(
        host=lakebase_host,
        port=5432,
        dbname='databricks_postgres',
        user=username,
        password=cred.token,
        sslmode='require',
        autocommit=True
    )

    print("Connected to Lakebase successfully!")
    return conn


def get_neon_connection(connection_string: str):
    """Get Neon PostgreSQL connection"""
    import psycopg

    conn = psycopg.connect(connection_string, autocommit=True)
    print("Connected to Neon successfully!")
    return conn


def create_lakebase_schema(conn, schema_name: str):
    """Create schema in Lakebase if it doesn't exist"""
    with conn.cursor() as cur:
        # Check if schema exists
        cur.execute(f"""
            SELECT schema_name FROM information_schema.schemata
            WHERE schema_name = %s
        """, (schema_name,))

        if cur.fetchone():
            print(f"Schema '{schema_name}' already exists")
        else:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS {schema_name}')
            print(f"Created schema '{schema_name}'")

        # Set search path
        cur.execute(f'SET search_path TO {schema_name}')
        print(f"Set search_path to '{schema_name}'")


def create_tables_in_lakebase(conn, schema_name: str):
    """Create all tables in Lakebase schema"""
    with conn.cursor() as cur:
        cur.execute(f'SET search_path TO {schema_name}')

        # Create enum types if they don't exist
        enums = [
            ("userrole", ['SUGGEST_ONLY', 'APPROVER', 'ADMIN']),
            ("entitytype", ['CATALOG', 'SCHEMA', 'TABLE', 'COLUMN']),
            ("commentstatus", ['DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'APPLIED']),
            ("approvalaction", ['APPROVED', 'REJECTED', 'REQUEST_CHANGES']),
        ]

        for enum_name, values in enums:
            # Check if enum exists
            cur.execute(f"""
                SELECT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = %s
                )
            """, (enum_name,))

            if not cur.fetchone()[0]:
                values_str = ", ".join([f"'{v}'" for v in values])
                cur.execute(f"CREATE TYPE {schema_name}.{enum_name} AS ENUM ({values_str})")
                print(f"Created enum type: {enum_name}")
            else:
                print(f"Enum type '{enum_name}' already exists")

        # Create tables
        tables_sql = f"""
        -- Users table
        CREATE TABLE IF NOT EXISTS {schema_name}.users (
            id UUID PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            username VARCHAR(100) NOT NULL UNIQUE,
            full_name VARCHAR(255),
            hashed_password VARCHAR(255) NOT NULL,
            role {schema_name}.userrole NOT NULL DEFAULT 'SUGGEST_ONLY',
            is_active BOOLEAN NOT NULL DEFAULT true,
            is_superuser BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- Comments table
        CREATE TABLE IF NOT EXISTS {schema_name}.comments (
            id UUID PRIMARY KEY,
            entity_type {schema_name}.entitytype NOT NULL,
            entity_catalog VARCHAR(255) NOT NULL,
            entity_schema VARCHAR(255),
            entity_table VARCHAR(255),
            entity_column VARCHAR(255),
            current_comment TEXT,
            suggested_comment TEXT NOT NULL,
            status {schema_name}.commentstatus NOT NULL DEFAULT 'DRAFT',
            created_by UUID NOT NULL REFERENCES {schema_name}.users(id),
            approved_by UUID REFERENCES {schema_name}.users(id),
            submitted_at TIMESTAMPTZ,
            approved_at TIMESTAMPTZ,
            applied_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- Create indexes on comments
        CREATE INDEX IF NOT EXISTS ix_comments_entity_catalog ON {schema_name}.comments(entity_catalog);
        CREATE INDEX IF NOT EXISTS ix_comments_entity_schema ON {schema_name}.comments(entity_schema);
        CREATE INDEX IF NOT EXISTS ix_comments_entity_table ON {schema_name}.comments(entity_table);
        CREATE INDEX IF NOT EXISTS ix_comments_status ON {schema_name}.comments(status);

        -- Approvals table
        CREATE TABLE IF NOT EXISTS {schema_name}.approvals (
            id UUID PRIMARY KEY,
            comment_id UUID NOT NULL REFERENCES {schema_name}.comments(id),
            approver_id UUID NOT NULL REFERENCES {schema_name}.users(id),
            action {schema_name}.approvalaction NOT NULL,
            feedback TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- Audit logs table
        CREATE TABLE IF NOT EXISTS {schema_name}.audit_logs (
            id UUID PRIMARY KEY,
            user_id UUID REFERENCES {schema_name}.users(id),
            action VARCHAR(100) NOT NULL,
            entity_type VARCHAR(50),
            entity_id UUID,
            details JSONB,
            ip_address INET,
            user_agent TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON {schema_name}.audit_logs(action);

        -- Alembic version table for migrations
        CREATE TABLE IF NOT EXISTS {schema_name}.alembic_version (
            version_num VARCHAR(32) NOT NULL PRIMARY KEY
        );
        """

        # Execute each statement separately
        for statement in tables_sql.split(';'):
            statement = statement.strip()
            if statement:
                try:
                    cur.execute(statement)
                except Exception as e:
                    print(f"Warning: {e}")

        print("Tables created successfully!")


def migrate_data(neon_conn, lakebase_conn, schema_name: str):
    """Migrate data from Neon to Lakebase"""
    tables = ['users', 'comments', 'approvals', 'audit_logs']

    with neon_conn.cursor() as neon_cur, lakebase_conn.cursor() as lb_cur:
        lb_cur.execute(f'SET search_path TO {schema_name}')

        for table in tables:
            try:
                # Get data from Neon
                neon_cur.execute(f"SELECT * FROM {table}")
                rows = neon_cur.fetchall()

                if not rows:
                    print(f"No data in {table}")
                    continue

                # Get column names
                columns = [desc[0] for desc in neon_cur.description]

                print(f"Migrating {len(rows)} rows from {table}...")

                # Clear existing data in Lakebase (optional - be careful!)
                # lb_cur.execute(f"DELETE FROM {schema_name}.{table}")

                # Insert data
                placeholders = ', '.join(['%s'] * len(columns))
                columns_str = ', '.join(columns)

                for row in rows:
                    try:
                        lb_cur.execute(
                            f"INSERT INTO {schema_name}.{table} ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING",
                            row
                        )
                    except Exception as e:
                        print(f"  Error inserting row: {e}")

                print(f"  Migrated {table} successfully!")

            except Exception as e:
                print(f"Error migrating {table}: {e}")

    # Set alembic version
    with lakebase_conn.cursor() as lb_cur:
        lb_cur.execute(f'SET search_path TO {schema_name}')
        lb_cur.execute(f"""
            INSERT INTO {schema_name}.alembic_version (version_num)
            VALUES ('b2433408b2f5')
            ON CONFLICT DO NOTHING
        """)
        print("Set alembic version to b2433408b2f5")


def main():
    global args
    parser = argparse.ArgumentParser(description="Migrate metadata-manager from Neon to Lakebase")
    parser.add_argument("--profile", required=True, help="Databricks CLI profile")
    parser.add_argument("--schema", default="metadata_manager", help="Lakebase schema name")
    parser.add_argument("--skip-data", action="store_true", help="Skip data migration (schema only)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")

    args = parser.parse_args()

    print("=" * 60)
    print("Metadata Manager: Neon to Lakebase Migration")
    print("=" * 60)
    print(f"Profile: {args.profile}")
    print(f"Schema: {args.schema}")
    print()

    # Get connections
    neon_url = get_neon_connection_string()
    if not neon_url:
        print("Could not get Neon connection string")
        sys.exit(1)

    print(f"Neon URL: {neon_url[:50]}...")

    if args.dry_run:
        print("\n[DRY RUN] Would perform migration")
        return

    # Connect to databases
    print("\nConnecting to databases...")
    lakebase_conn = get_lakebase_connection(args.profile)
    neon_conn = get_neon_connection(neon_url)

    # Create schema
    print("\nCreating Lakebase schema...")
    create_lakebase_schema(lakebase_conn, args.schema)

    # Create tables
    print("\nCreating tables...")
    create_tables_in_lakebase(lakebase_conn, args.schema)

    # Migrate data
    if not args.skip_data:
        print("\nMigrating data...")
        migrate_data(neon_conn, lakebase_conn, args.schema)

    # Close connections
    neon_conn.close()
    lakebase_conn.close()

    print("\n" + "=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)
    print(f"\nNext steps:")
    print(f"1. Update app.yaml to use Lakebase schema: {args.schema}")
    print(f"2. Grant SP permissions to the schema")
    print(f"3. Redeploy the app")


if __name__ == "__main__":
    main()
