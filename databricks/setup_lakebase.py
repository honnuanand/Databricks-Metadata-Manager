#!/usr/bin/env python3
"""
Setup script for Databricks Lakebase.

This script:
1. Connects to your Lakebase instance using OAuth
2. Creates the required tables
3. Seeds initial users

Usage:
    python databricks/setup_lakebase.py

Requirements:
    - databricks-sdk >= 0.56.0
    - psycopg2-binary or psycopg2
    - passlib[bcrypt]
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


# Configuration for your Lakebase instance
LAKEBASE_CONFIG = {
    "host": "instance-f2a8b56a-7fe2-4c9c-a0a3-7768594a50e5.database.cloud.databricks.com",
    "port": 5432,
    "database": "databricks_postgres",
    "user": "anand.rao@databricks.com",
    # Instance name from Databricks (use the name, not the hostname)
    "instance_name": "arao-lb",
}


# Seed users with bcrypt-hashed passwords
SEED_USERS = [
    {
        "id": "00000000-0000-0000-0000-000000000001",
        "email": "admin@example.com",
        "username": "admin",
        "full_name": "Admin User",
        "password": "admin123",
        "role": "ADMIN",
        "is_superuser": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000000002",
        "email": "approver@example.com",
        "username": "approver",
        "full_name": "Approver User",
        "password": "approver123",
        "role": "APPROVER",
        "is_superuser": False,
    },
    {
        "id": "00000000-0000-0000-0000-000000000003",
        "email": "user@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "password": "user123",
        "role": "SUGGEST_ONLY",
        "is_superuser": False,
    },
]


def get_oauth_token(instance_name: str) -> str:
    """Generate OAuth token for Lakebase authentication."""
    try:
        from databricks.sdk import WorkspaceClient

        print(f"Generating OAuth token for instance: {instance_name}")
        w = WorkspaceClient()
        cred = w.database.generate_database_credential(
            request_id=str(uuid.uuid4()),
            instance_names=[instance_name]
        )
        print("OAuth token generated successfully")
        return cred.token
    except ImportError:
        print("ERROR: databricks-sdk not installed. Run: pip install databricks-sdk>=0.56.0")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to generate OAuth token: {e}")
        sys.exit(1)


def get_connection(config: dict):
    """Get psycopg2 connection to Lakebase."""
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
        sys.exit(1)

    token = get_oauth_token(config["instance_name"])

    print(f"Connecting to Lakebase at {config['host']}...")
    conn = psycopg2.connect(
        host=config["host"],
        port=config["port"],
        database=config["database"],
        user=config["user"],
        password=token,
        sslmode="require"
    )
    print("Connected to Lakebase successfully!")
    return conn


def create_tables(conn):
    """Create all required tables."""
    print("\nCreating tables...")

    with conn.cursor() as cur:
        # Enable UUID extension
        cur.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")

        # Users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(100) UNIQUE NOT NULL,
                full_name VARCHAR(255),
                hashed_password VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL CHECK (role IN ('SUGGEST_ONLY', 'APPROVER', 'ADMIN')),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);")
        print("  - users table created")

        # Comments table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('CATALOG', 'SCHEMA', 'TABLE', 'COLUMN')),
                entity_catalog VARCHAR(255) NOT NULL,
                entity_schema VARCHAR(255),
                entity_table VARCHAR(255),
                entity_column VARCHAR(255),
                current_comment TEXT,
                suggested_comment TEXT NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PENDING', 'APPROVED', 'REJECTED', 'APPLIED')),
                created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
                submitted_at TIMESTAMPTZ,
                approved_at TIMESTAMPTZ,
                applied_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_comments_status ON comments(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_comments_created_by ON comments(created_by);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_comments_entity_type ON comments(entity_type);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_comments_entity_catalog ON comments(entity_catalog);")
        print("  - comments table created")

        # Approvals table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                comment_id UUID NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
                approver_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
                action VARCHAR(20) NOT NULL CHECK (action IN ('APPROVED', 'REJECTED', 'REQUEST_CHANGES')),
                feedback TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_approvals_comment_id ON approvals(comment_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_approvals_approver_id ON approvals(approver_id);")
        print("  - approvals table created")

        # Audit logs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                action VARCHAR(100) NOT NULL,
                entity_type VARCHAR(50),
                entity_id UUID,
                details JSONB,
                ip_address INET,
                user_agent TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);")
        print("  - audit_logs table created")

        # Alembic version table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            );
        """)
        cur.execute("""
            INSERT INTO alembic_version (version_num)
            VALUES ('b2433408b2f5')
            ON CONFLICT (version_num) DO NOTHING;
        """)
        print("  - alembic_version table created")

    conn.commit()
    print("All tables created successfully!")


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(password)
    except ImportError:
        print("ERROR: passlib not installed. Run: pip install passlib[bcrypt]")
        sys.exit(1)


def seed_users(conn):
    """Seed initial users into the database."""
    print("\nSeeding users...")

    with conn.cursor() as cur:
        # Check if users exist
        cur.execute("SELECT COUNT(*) FROM users;")
        count = cur.fetchone()[0]

        if count > 0:
            print(f"  Users table already has {count} records - skipping seed")
            return

        now = datetime.now(timezone.utc)

        for user in SEED_USERS:
            hashed_password = hash_password(user["password"])
            cur.execute("""
                INSERT INTO users (id, email, username, full_name, hashed_password, role, is_active, is_superuser, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING;
            """, (
                user["id"],
                user["email"],
                user["username"],
                user["full_name"],
                hashed_password,
                user["role"],
                True,
                user["is_superuser"],
                now,
                now
            ))
            print(f"  - Created user: {user['username']} ({user['role']})")

    conn.commit()
    print("Users seeded successfully!")


def verify_setup(conn):
    """Verify the setup was successful."""
    print("\nVerifying setup...")

    with conn.cursor() as cur:
        # Check tables
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]
        print(f"  Tables: {', '.join(tables)}")

        # Check users
        cur.execute("SELECT username, role FROM users ORDER BY id;")
        users = cur.fetchall()
        print(f"  Users: {', '.join(f'{u[0]} ({u[1]})' for u in users)}")

    print("\nSetup complete!")


def print_env_config():
    """Print environment configuration for .env file."""
    print("\n" + "=" * 60)
    print("Add the following to your .env file:")
    print("=" * 60)
    print(f"""
# Lakebase Configuration
LAKEBASE_HOST={LAKEBASE_CONFIG['host']}
LAKEBASE_PORT={LAKEBASE_CONFIG['port']}
LAKEBASE_DATABASE={LAKEBASE_CONFIG['database']}
LAKEBASE_USER={LAKEBASE_CONFIG['user']}
LAKEBASE_INSTANCE={LAKEBASE_CONFIG['instance_name']}
LAKEBASE_USE_OAUTH=true

# For Databricks Apps, OAuth is handled automatically.
# For local development, ensure you have Databricks CLI configured.
""")
    print("=" * 60)
    print("\nTest user credentials:")
    print("  admin@example.com / admin123 (ADMIN)")
    print("  approver@example.com / approver123 (APPROVER)")
    print("  user@example.com / user123 (SUGGEST_ONLY)")


def main():
    print("=" * 60)
    print("Lakebase Setup for Metadata Manager")
    print("=" * 60)

    conn = get_connection(LAKEBASE_CONFIG)

    try:
        create_tables(conn)
        seed_users(conn)
        verify_setup(conn)
        print_env_config()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
