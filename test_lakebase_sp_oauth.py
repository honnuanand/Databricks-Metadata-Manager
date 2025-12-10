#!/usr/bin/env python3
"""
Test script to set up and test OAuth authentication for a Service Principal with Lakebase.

Prerequisites:
1. Connect to Lakebase as admin and run:
   - CREATE EXTENSION IF NOT EXISTS databricks_auth;
   - SELECT databricks_create_role('<sp-client-id>', 'SERVICE_PRINCIPAL');
   - GRANT ALL PRIVILEGES ON DATABASE databricks_postgres TO "<role-name>";
   - GRANT ALL PRIVILEGES ON SCHEMA public TO "<role-name>";
   - GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "<role-name>";

2. The service principal must have appropriate Databricks workspace permissions.
"""
import os
import sys

# Configuration for FEVM workspace
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST", "https://fe-vm-leaps-fe.cloud.databricks.com")
LAKEBASE_INSTANCE = os.environ.get("LAKEBASE_INSTANCE", "arao-lb")
LAKEBASE_HOST = os.environ.get("LAKEBASE_HOST", "instance-f2a8b56a-7fe2-4c9c-a0a3-7768594a50e5.database.cloud.databricks.com")

# Service Principal details (from Databricks Apps)
SP_CLIENT_ID = "10922e0f-2688-4911-9fe0-4f35af5a563f"
SP_NAME = "app-1i54xz metadata-manager"


def step1_check_current_lakebase_roles():
    """Step 1: Check what roles exist in Lakebase currently"""
    print("=" * 60)
    print("Step 1: Checking current Lakebase roles")
    print("=" * 60)

    try:
        import psycopg2

        # Connect with admin credentials (using current OAuth token from test_lakebase_oauth.py)
        # Or use static password if available
        lakebase_password = os.environ.get("LAKEBASE_PASSWORD")
        lakebase_user = os.environ.get("LAKEBASE_USER", "metadata_manager_app")

        if not lakebase_password:
            print("  Set LAKEBASE_PASSWORD environment variable to check roles")
            print("  Or connect manually using psql/DBeaver")
            return None

        conn = psycopg2.connect(
            host=LAKEBASE_HOST,
            port=5432,
            database="databricks_postgres",
            user=lakebase_user,
            password=lakebase_password,
            sslmode="require"
        )

        cursor = conn.cursor()

        # List all roles
        print("\n  Existing roles:")
        cursor.execute("SELECT rolname FROM pg_roles ORDER BY rolname")
        for row in cursor.fetchall():
            print(f"    - {row[0]}")

        # Check if databricks_auth extension exists
        print("\n  Checking for databricks_auth extension:")
        cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'databricks_auth'")
        ext = cursor.fetchone()
        if ext:
            print("    ✓ databricks_auth extension is installed")
        else:
            print("    ✗ databricks_auth extension NOT installed")
            print("    Run: CREATE EXTENSION IF NOT EXISTS databricks_auth;")

        cursor.close()
        conn.close()
        return True

    except ImportError:
        print("  ✗ psycopg2 not installed")
        return False
    except Exception as e:
        print(f"  ✗ Error: {type(e).__name__}: {e}")
        return False


def step2_show_setup_commands():
    """Step 2: Show the SQL commands needed to set up SP OAuth"""
    print("\n" + "=" * 60)
    print("Step 2: SQL Commands to Enable SP OAuth")
    print("=" * 60)

    print(f"""
Connect to Lakebase as an admin user and run these commands:

-- 1. Create the databricks_auth extension (if not exists)
CREATE EXTENSION IF NOT EXISTS databricks_auth;

-- 2. Create Postgres role for the Service Principal
-- This maps the SP's client_id to a Postgres role
SELECT databricks_create_role('{SP_CLIENT_ID}', 'SERVICE_PRINCIPAL');

-- 3. The role name will be the SP's client_id
-- Grant permissions to this role:
GRANT ALL PRIVILEGES ON DATABASE databricks_postgres TO "{SP_CLIENT_ID}";
GRANT ALL PRIVILEGES ON SCHEMA public TO "{SP_CLIENT_ID}";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{SP_CLIENT_ID}";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "{SP_CLIENT_ID}";

-- 4. Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT ALL PRIVILEGES ON TABLES TO "{SP_CLIENT_ID}";

-- Verify the role was created:
SELECT rolname FROM pg_roles WHERE rolname LIKE '%{SP_CLIENT_ID[:8]}%';
""")


def step3_test_sp_oauth_from_app_context():
    """Step 3: Explain how to test SP OAuth from within the app"""
    print("\n" + "=" * 60)
    print("Step 3: Testing SP OAuth from Databricks Apps")
    print("=" * 60)

    print(f"""
When running inside Databricks Apps, the service principal credentials
are available via environment variables:
  - DATABRICKS_CLIENT_ID
  - DATABRICKS_CLIENT_SECRET

To test OAuth with the SP:

1. The app code would use WorkspaceClient() without explicit credentials
   (it auto-discovers OAuth from environment)

2. Call w.database.generate_database_credential() to get a token

3. Use the token as password in psycopg2.connect()

Key difference from user OAuth:
- User OAuth: username = user's email (e.g., anand.rao@databricks.com)
- SP OAuth: username = SP's client_id ({SP_CLIENT_ID})

The Lakebase Postgres role must match what OAuth returns as the username.
""")


def step4_show_app_code_changes():
    """Step 4: Show what code changes would be needed in the app"""
    print("\n" + "=" * 60)
    print("Step 4: App Code Changes for SP OAuth")
    print("=" * 60)

    print("""
Here's how the app could use SP OAuth for Lakebase:

```python
# In backend/app/db/lakebase_oauth.py (new file)

import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from databricks.sdk import WorkspaceClient

class LakebaseOAuthManager:
    \"\"\"Manages OAuth tokens for Lakebase with automatic refresh\"\"\"

    def __init__(self, lakebase_instance: str, lakebase_host: str):
        self.lakebase_instance = lakebase_instance
        self.lakebase_host = lakebase_host
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._workspace_client: Optional[WorkspaceClient] = None
        self.refresh_buffer_seconds = 300  # Refresh 5 min before expiry

    def _get_workspace_client(self) -> WorkspaceClient:
        if self._workspace_client is None:
            # Auto-discovers OAuth credentials from environment
            # (DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET)
            self._workspace_client = WorkspaceClient()
        return self._workspace_client

    def _generate_token(self) -> Tuple[str, datetime]:
        w = self._get_workspace_client()
        cred = w.database.generate_database_credential(
            request_id=str(uuid.uuid4()),
            instance_names=[self.lakebase_instance]
        )
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        return cred.token, expiry

    def get_token(self) -> str:
        now = datetime.now(timezone.utc)
        needs_refresh = (
            self._token is None or
            self._token_expiry is None or
            (self._token_expiry - now).total_seconds() < self.refresh_buffer_seconds
        )
        if needs_refresh:
            self._token, self._token_expiry = self._generate_token()
        return self._token

    def get_username(self) -> str:
        # For SP, username is the client_id
        return os.environ.get('DATABRICKS_CLIENT_ID')

    def get_database_url(self) -> str:
        from urllib.parse import quote_plus
        token = self.get_token()
        username = self.get_username()
        return f"postgresql://{quote_plus(username)}:{quote_plus(token)}@{self.lakebase_host}:5432/databricks_postgres?sslmode=require"
```

Then in the SQLAlchemy session factory, use a connection factory that
refreshes tokens before creating connections.
""")


def main():
    print("=" * 60)
    print("Service Principal OAuth for Lakebase - Setup Guide")
    print("=" * 60)
    print(f"\nService Principal: {SP_NAME}")
    print(f"Client ID: {SP_CLIENT_ID}")
    print(f"Lakebase Instance: {LAKEBASE_INSTANCE}")
    print(f"Lakebase Host: {LAKEBASE_HOST}")

    step1_check_current_lakebase_roles()
    step2_show_setup_commands()
    step3_test_sp_oauth_from_app_context()
    step4_show_app_code_changes()

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print("""
To enable SP OAuth for Lakebase:

1. Run the SQL commands in Step 2 (as Lakebase admin)
2. Implement LakebaseOAuthManager in the app (Step 4)
3. Update the database session to use OAuth tokens
4. Deploy and test

Benefits of SP OAuth over static password:
- No long-lived passwords to manage/rotate
- Tokens auto-expire after 1 hour
- Better audit trail (SP identity in logs)
- Follows Databricks security best practices
""")


if __name__ == "__main__":
    main()
