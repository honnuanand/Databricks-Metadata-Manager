#!/usr/bin/env python3
"""
Setup Lakebase schema for metadata-manager deployment.

This script:
1. Creates the schema in Lakebase if it doesn't exist
2. Creates all required tables with proper types
3. Creates default users for testing
4. Grants access to the Databricks App Service Principal

Usage:
    # New workspace setup (schema + tables + default users)
    python scripts/setup_lakebase_schema.py --profile fe-vm-leaps-fe --schema metadata_manager

    # Setup and grant SP access for an existing app
    python scripts/setup_lakebase_schema.py --profile fe-vm-leaps-fe --schema metadata_manager --app-name metadata-mgr

    # Schema only (no SP grants)
    python scripts/setup_lakebase_schema.py --profile fe-vm-leaps-fe --schema metadata_manager --skip-sp-grants

Requirements:
    - databricks-sdk
    - psycopg (pip install psycopg[binary])
    - bcrypt (pip install bcrypt)
"""

import argparse
import json
import subprocess
import sys
import os
import uuid
from datetime import datetime

# Default test users to create
DEFAULT_USERS = [
    {"username": "admin", "email": "admin@example.com", "password": "admin123", "role": "ADMIN", "is_superuser": True},
    {"username": "approver", "email": "approver@example.com", "password": "approver123", "role": "APPROVER", "is_superuser": False},
    {"username": "testuser", "email": "testuser@example.com", "password": "user123", "role": "SUGGEST_ONLY", "is_superuser": False},
]


def get_lakebase_connection(profile: str, lakebase_instance: str, lakebase_host: str):
    """Get Lakebase connection using OAuth"""
    from databricks.sdk import WorkspaceClient
    import psycopg

    print(f"Connecting to Lakebase...")
    print(f"  Instance: {lakebase_instance}")
    print(f"  Host: {lakebase_host}")

    # Create workspace client with profile
    w = WorkspaceClient(profile=profile)

    # Get current user for username
    me = w.current_user.me()
    username = me.user_name
    print(f"  User: {username}")

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

    print("  Connected!")
    return conn, w


def create_schema_if_not_exists(conn, schema_name: str) -> bool:
    """Create schema in Lakebase if it doesn't exist. Returns True if created."""
    with conn.cursor() as cur:
        # Check if schema exists
        cur.execute("""
            SELECT schema_name FROM information_schema.schemata
            WHERE schema_name = %s
        """, (schema_name,))

        if cur.fetchone():
            print(f"Schema '{schema_name}' already exists")
            return False
        else:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS {schema_name}')
            print(f"Created schema '{schema_name}'")
            return True


def create_tables(conn, schema_name: str):
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
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = %s
                )
            """, (enum_name,))

            if not cur.fetchone()[0]:
                values_str = ", ".join([f"'{v}'" for v in values])
                cur.execute(f"CREATE TYPE {schema_name}.{enum_name} AS ENUM ({values_str})")
                print(f"  Created enum type: {enum_name}")
            else:
                print(f"  Enum type '{enum_name}' already exists")

        # Create tables
        tables = [
            # Users table
            f"""
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
            )
            """,
            # Comments table
            f"""
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
            )
            """,
            # Indexes on comments
            f"CREATE INDEX IF NOT EXISTS ix_comments_entity_catalog ON {schema_name}.comments(entity_catalog)",
            f"CREATE INDEX IF NOT EXISTS ix_comments_entity_schema ON {schema_name}.comments(entity_schema)",
            f"CREATE INDEX IF NOT EXISTS ix_comments_entity_table ON {schema_name}.comments(entity_table)",
            f"CREATE INDEX IF NOT EXISTS ix_comments_status ON {schema_name}.comments(status)",
            # Approvals table
            f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.approvals (
                id UUID PRIMARY KEY,
                comment_id UUID NOT NULL REFERENCES {schema_name}.comments(id),
                approver_id UUID NOT NULL REFERENCES {schema_name}.users(id),
                action {schema_name}.approvalaction NOT NULL,
                feedback TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """,
            # Audit logs table
            f"""
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
            )
            """,
            f"CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON {schema_name}.audit_logs(action)",
            # Alembic version table for migrations
            f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.alembic_version (
                version_num VARCHAR(32) NOT NULL PRIMARY KEY
            )
            """,
        ]

        for sql in tables:
            sql = sql.strip()
            if sql:
                try:
                    cur.execute(sql)
                except Exception as e:
                    # Ignore "already exists" errors
                    if "already exists" not in str(e).lower():
                        print(f"  Warning: {e}")

        # Set alembic version
        cur.execute(f"""
            INSERT INTO {schema_name}.alembic_version (version_num)
            VALUES ('b2433408b2f5')
            ON CONFLICT DO NOTHING
        """)

        print("  Tables created successfully!")


def create_default_users(conn, schema_name: str):
    """Create default test users"""
    import bcrypt

    with conn.cursor() as cur:
        cur.execute(f'SET search_path TO {schema_name}')

        for user in DEFAULT_USERS:
            # Check if user exists
            cur.execute(f"SELECT id FROM {schema_name}.users WHERE username = %s", (user['username'],))
            if cur.fetchone():
                print(f"  User '{user['username']}' already exists")
                continue

            # Hash password
            hashed = bcrypt.hashpw(user['password'].encode(), bcrypt.gensalt()).decode()

            # Insert user
            cur.execute(f"""
                INSERT INTO {schema_name}.users (id, email, username, full_name, hashed_password, role, is_active, is_superuser, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, true, %s, NOW(), NOW())
            """, (
                str(uuid.uuid4()),
                user['email'],
                user['username'],
                user['username'].title(),
                hashed,
                user['role'],
                user['is_superuser']
            ))
            print(f"  Created user '{user['username']}' (role: {user['role']})")


def get_app_sp_info(app_name: str, profile: str) -> dict:
    """Get Service Principal info from Databricks App"""
    result = subprocess.run(
        ["databricks", "apps", "get", app_name, "--profile", profile, "--output", "json"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"  Warning: Could not get app info: {result.stderr.strip()}")
        return None

    app_info = json.loads(result.stdout)

    return {
        "client_id": app_info.get("service_principal_client_id"),
        "sp_id": app_info.get("service_principal_id"),
        "sp_name": app_info.get("service_principal_name"),
    }


def grant_sp_access(conn, sp_client_id: str, sp_id: int, schema_name: str):
    """Grant Lakebase access to the Service Principal"""
    with conn.cursor() as cur:
        # 1. Create PostgreSQL role with SP client ID as name
        print(f"  Creating PostgreSQL role: {sp_client_id[:20]}...")
        try:
            cur.execute(f'CREATE ROLE "{sp_client_id}" WITH LOGIN NOINHERIT')
            print(f"    Role created!")
        except Exception as e:
            if "already exists" in str(e):
                print(f"    Role already exists")
            else:
                print(f"    Warning: {e}")

        # 2. Set security label for OAuth authentication
        label = f"id={sp_id},type=SERVICE_PRINCIPAL"
        print(f"  Setting security label: {label}")
        try:
            cur.execute(f'''
                SECURITY LABEL FOR databricks_auth ON ROLE "{sp_client_id}" IS '{label}'
            ''')
            print(f"    Security label set!")
        except Exception as e:
            print(f"    Warning: {e}")

        # 3. Grant schema permissions
        print(f"  Granting permissions on schema '{schema_name}'...")
        grants = [
            f'GRANT USAGE ON SCHEMA {schema_name} TO "{sp_client_id}"',
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {schema_name} TO "{sp_client_id}"',
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{sp_client_id}"',
            f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {schema_name} TO "{sp_client_id}"',
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT USAGE, SELECT ON SEQUENCES TO "{sp_client_id}"',
        ]

        for grant in grants:
            try:
                cur.execute(grant)
            except Exception as e:
                print(f"    Warning: {e}")

        print(f"    Permissions granted!")


def main():
    parser = argparse.ArgumentParser(description="Setup Lakebase schema for metadata-manager")
    parser.add_argument("--profile", required=True, help="Databricks CLI profile")
    parser.add_argument("--schema", default="metadata_manager", help="Lakebase schema name")
    parser.add_argument("--app-name", help="Databricks App name (for SP grants)")
    parser.add_argument("--lakebase-instance", default="arao-lb", help="Lakebase instance name")
    parser.add_argument("--lakebase-host",
        default="instance-f2a8b56a-7fe2-4c9c-a0a3-7768594a50e5.database.cloud.databricks.com",
        help="Lakebase hostname")
    parser.add_argument("--skip-users", action="store_true", help="Skip creating default users")
    parser.add_argument("--skip-sp-grants", action="store_true", help="Skip SP permission grants")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")

    args = parser.parse_args()

    print("=" * 60)
    print("Metadata Manager: Lakebase Schema Setup")
    print("=" * 60)
    print(f"Profile: {args.profile}")
    print(f"Schema: {args.schema}")
    print(f"Instance: {args.lakebase_instance}")
    print()

    if args.dry_run:
        print("[DRY RUN] Would perform the following:")
        print(f"  1. Create schema '{args.schema}' if not exists")
        print(f"  2. Create tables (users, comments, approvals, audit_logs)")
        if not args.skip_users:
            print(f"  3. Create default users (admin, approver, testuser)")
        if not args.skip_sp_grants and args.app_name:
            print(f"  4. Grant SP access for app '{args.app_name}'")
        return

    # Connect to Lakebase
    conn, workspace_client = get_lakebase_connection(args.profile, args.lakebase_instance, args.lakebase_host)

    # 1. Create schema
    print("\n1. Creating schema...")
    schema_created = create_schema_if_not_exists(conn, args.schema)

    # 2. Create tables
    print("\n2. Creating tables...")
    create_tables(conn, args.schema)

    # 3. Create default users
    if not args.skip_users:
        print("\n3. Creating default users...")
        create_default_users(conn, args.schema)
    else:
        print("\n3. Skipping default users")

    # 4. Grant SP access
    if not args.skip_sp_grants and args.app_name:
        print(f"\n4. Granting SP access for app '{args.app_name}'...")
        sp_info = get_app_sp_info(args.app_name, args.profile)
        if sp_info and sp_info.get("client_id"):
            print(f"  SP Client ID: {sp_info['client_id']}")
            print(f"  SP ID: {sp_info['sp_id']}")
            grant_sp_access(conn, sp_info['client_id'], sp_info['sp_id'], args.schema)
        else:
            print(f"  Could not get SP info. Run grant script separately after app is created.")
    elif args.skip_sp_grants:
        print("\n4. Skipping SP grants")
    else:
        print("\n4. No app name provided, skipping SP grants")

    conn.close()

    print("\n" + "=" * 60)
    print("Setup completed!")
    print("=" * 60)
    print(f"\nNext steps:")
    if not args.app_name:
        print(f"  1. Deploy the app: python deploy_to_databricks.py --skip-secrets")
        print(f"  2. Grant SP access: python scripts/grant_lakebase_sp_access.py --profile {args.profile} --schema {args.schema}")
        print(f"  3. Redeploy to apply permissions: python deploy_to_databricks.py --skip-secrets")
    else:
        print(f"  1. Redeploy the app: python deploy_to_databricks.py --skip-secrets")


if __name__ == "__main__":
    main()
