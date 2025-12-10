#!/usr/bin/env python3
"""
Test script to explore OAuth token authentication for Lakebase
Includes token refresh logic for long-running applications
"""
import os
import uuid
import time
from datetime import datetime, timezone
from typing import Optional, Tuple

# Check SDK version
try:
    import databricks.sdk
    print(f"databricks-sdk version: {databricks.sdk.__version__}")
except:
    print("databricks-sdk not installed or version not found")

from databricks.sdk import WorkspaceClient

# Configuration
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST", "https://fe-vm-leaps-fe.cloud.databricks.com")
# The instance NAME (not the hostname UUID)
LAKEBASE_INSTANCE = os.environ.get("LAKEBASE_INSTANCE", "arao-lb")
# The actual hostname for PostgreSQL connections
LAKEBASE_HOST = os.environ.get("LAKEBASE_HOST", "instance-f2a8b56a-7fe2-4c9c-a0a3-7768594a50e5.database.cloud.databricks.com")


class LakebaseOAuthManager:
    """
    Manages OAuth tokens for Lakebase connections with automatic refresh.
    Tokens expire after 1 hour, so we refresh proactively.
    """

    def __init__(self, databricks_host: str, lakebase_instance: str, lakebase_host: str = None):
        self.databricks_host = databricks_host
        self.lakebase_instance = lakebase_instance  # The instance NAME (e.g., "arao-lb")
        # The actual PostgreSQL hostname (e.g., "instance-xxx.database.cloud.databricks.com")
        self.lakebase_host = lakebase_host or f"{lakebase_instance}.database.cloud.databricks.com"

        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._username: Optional[str] = None
        self._workspace_client: Optional[WorkspaceClient] = None

        # Refresh token 5 minutes before expiry
        self.refresh_buffer_seconds = 300

    def _get_workspace_client(self) -> WorkspaceClient:
        """Get or create WorkspaceClient"""
        if self._workspace_client is None:
            self._workspace_client = WorkspaceClient(host=self.databricks_host)
        return self._workspace_client

    def _generate_token(self) -> Tuple[str, datetime]:
        """Generate a new OAuth token for Lakebase"""
        w = self._get_workspace_client()

        # Get current user (for username)
        if self._username is None:
            self._username = w.current_user.me().user_name

        # Generate database credential
        cred = w.database.generate_database_credential(
            request_id=str(uuid.uuid4()),
            instance_names=[self.lakebase_instance]
        )

        # Parse expiration time
        expiry = None
        if hasattr(cred, 'expiration_time') and cred.expiration_time:
            # expiration_time is typically in ISO format or epoch
            try:
                if isinstance(cred.expiration_time, (int, float)):
                    expiry = datetime.fromtimestamp(cred.expiration_time / 1000, tz=timezone.utc)
                else:
                    expiry = datetime.fromisoformat(str(cred.expiration_time).replace('Z', '+00:00'))
            except:
                # Default to 1 hour from now
                expiry = datetime.now(timezone.utc).replace(microsecond=0)
                expiry = expiry.replace(hour=expiry.hour + 1)
        else:
            # Default to 1 hour from now
            from datetime import timedelta
            expiry = datetime.now(timezone.utc) + timedelta(hours=1)

        return cred.token, expiry

    def get_token(self) -> str:
        """Get a valid OAuth token, refreshing if needed"""
        now = datetime.now(timezone.utc)

        # Check if we need to refresh
        needs_refresh = (
            self._token is None or
            self._token_expiry is None or
            (self._token_expiry - now).total_seconds() < self.refresh_buffer_seconds
        )

        if needs_refresh:
            print(f"[{now.isoformat()}] Refreshing OAuth token...")
            self._token, self._token_expiry = self._generate_token()
            print(f"  New token expires at: {self._token_expiry.isoformat()}")

        return self._token

    def get_username(self) -> str:
        """Get the username (Databricks identity) for PostgreSQL connection"""
        if self._username is None:
            w = self._get_workspace_client()
            self._username = w.current_user.me().user_name
        return self._username

    def get_connection_params(self) -> dict:
        """Get PostgreSQL connection parameters with fresh token"""
        return {
            "host": self.lakebase_host,
            "port": 5432,
            "database": "databricks_postgres",
            "user": self.get_username(),
            "password": self.get_token(),
            "sslmode": "require"
        }

    def get_database_url(self) -> str:
        """Get a DATABASE_URL string with fresh token"""
        from urllib.parse import quote_plus
        token = self.get_token()
        username = self.get_username()
        return f"postgresql://{quote_plus(username)}:{quote_plus(token)}@{self.lakebase_host}:5432/databricks_postgres?sslmode=require"

    @property
    def token_expires_in(self) -> Optional[int]:
        """Seconds until token expires"""
        if self._token_expiry is None:
            return None
        return int((self._token_expiry - datetime.now(timezone.utc)).total_seconds())


def test_oauth_connection():
    """Test OAuth token generation and connection"""

    print("=" * 60)
    print("Testing Lakebase OAuth Token Authentication")
    print("=" * 60)
    print(f"Databricks Host: {DATABRICKS_HOST}")
    print(f"Lakebase Instance: {LAKEBASE_INSTANCE}")
    print(f"Lakebase Host: {LAKEBASE_HOST}")
    print()

    # Step 1: Create OAuth manager
    print("Step 1: Creating OAuth Manager...")
    try:
        oauth_mgr = LakebaseOAuthManager(DATABRICKS_HOST, LAKEBASE_INSTANCE, LAKEBASE_HOST)
        print("  ✓ OAuth Manager created")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

    # Step 2: Get username (authenticates to Databricks)
    print("\nStep 2: Getting Databricks identity...")
    try:
        username = oauth_mgr.get_username()
        print(f"  ✓ Authenticated as: {username}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

    # Step 3: Generate OAuth token
    print("\nStep 3: Generating OAuth token...")
    try:
        token = oauth_mgr.get_token()
        print(f"  ✓ Token generated!")
        print(f"  Token prefix: {token[:40]}...")
        print(f"  Expires in: {oauth_mgr.token_expires_in} seconds")
    except AttributeError as e:
        print(f"  ✗ Method not found: {e}")
        print("    The database.generate_database_credential() method may not be available")
        print("    Requires databricks-sdk >= 0.57.0")
        return False
    except Exception as e:
        print(f"  ✗ Failed: {type(e).__name__}: {e}")
        return False

    # Step 4: Connect to PostgreSQL with OAuth token
    print("\nStep 4: Connecting to Lakebase with OAuth token...")
    try:
        import psycopg2

        params = oauth_mgr.get_connection_params()
        print(f"  Username: {params['user']}")
        print(f"  Password: <oauth-token>")
        print(f"  Host: {params['host']}")

        conn = psycopg2.connect(**params)

        cursor = conn.cursor()
        cursor.execute("SELECT current_user, current_database()")
        result = cursor.fetchone()
        print(f"  ✓ Connected!")
        print(f"  Current user: {result[0]}")
        print(f"  Current database: {result[1]}")

        # Try a simple query
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables")
        count = cursor.fetchone()[0]
        print(f"  Tables accessible: {count}")

        cursor.close()
        conn.close()
        print("  ✓ Connection closed")

    except ImportError:
        print("  ✗ psycopg2 not installed")
        return False
    except Exception as e:
        print(f"  ✗ Connection failed: {type(e).__name__}: {e}")
        return False

    # Step 5: Test token refresh
    print("\nStep 5: Testing token refresh logic...")
    print(f"  Current token expires in: {oauth_mgr.token_expires_in} seconds")
    print("  Simulating token near expiry by setting low buffer...")

    # Force refresh by setting buffer higher than time remaining
    original_buffer = oauth_mgr.refresh_buffer_seconds
    oauth_mgr.refresh_buffer_seconds = oauth_mgr.token_expires_in + 100  # Force refresh

    token2 = oauth_mgr.get_token()
    print(f"  ✓ Got refreshed token")
    print(f"  New token expires in: {oauth_mgr.token_expires_in} seconds")

    oauth_mgr.refresh_buffer_seconds = original_buffer

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)

    # Print summary
    print("\n📋 Summary: How to use OAuth for Lakebase")
    print("-" * 40)
    print("""
1. Create LakebaseOAuthManager instance
2. Call get_connection_params() or get_database_url() before each DB operation
3. The manager automatically refreshes tokens before expiry

Example usage in FastAPI:

    oauth_mgr = LakebaseOAuthManager(DATABRICKS_HOST, LAKEBASE_INSTANCE)

    def get_db_connection():
        return psycopg2.connect(**oauth_mgr.get_connection_params())

For SQLAlchemy with connection pooling, you'd need a custom
connection factory that refreshes tokens.
""")

    return True


if __name__ == "__main__":
    test_oauth_connection()
