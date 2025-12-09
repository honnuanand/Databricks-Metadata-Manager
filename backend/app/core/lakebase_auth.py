"""
Lakebase OAuth Authentication Manager.

Manages OAuth token generation and refresh for Databricks Lakebase connections.
Tokens expire after 1 hour but are only validated at connection time.
"""

import uuid
import threading
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class LakebaseAuthManager:
    """Manages OAuth token authentication for Lakebase.

    This is a singleton class that handles token generation and caching.
    Tokens are automatically refreshed before expiry (with 5-minute buffer).

    Usage:
        from app.core.lakebase_auth import lakebase_auth

        # Configure with instance name
        lakebase_auth.configure(instance_name="your-instance")

        # Get token for connection
        token = lakebase_auth.get_token()

        # Or get full connection string
        url = lakebase_auth.get_connection_string(
            host="instance.database.cloud.databricks.com",
            database="databricks_postgres",
            user="user@databricks.com"
        )
    """

    _instance: Optional['LakebaseAuthManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False):
            return
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._instance_name: Optional[str] = None
        self._initialized = True

    def configure(self, instance_name: str) -> None:
        """Configure the auth manager with Lakebase instance name.

        Args:
            instance_name: The Lakebase instance name (not full hostname)
        """
        self._instance_name = instance_name
        # Clear cached token when reconfiguring
        self._token = None
        self._token_expiry = None

    def get_token(self) -> str:
        """Get a valid OAuth token, refreshing if necessary.

        Returns:
            OAuth token string to use as password in connection

        Raises:
            RuntimeError: If instance not configured or SDK unavailable
        """
        if not self._instance_name:
            raise RuntimeError("LakebaseAuthManager not configured. Call configure() first.")

        # Return cached token if still valid (with 5-minute buffer)
        if self._token and self._token_expiry:
            if self._token_expiry > datetime.now() + timedelta(minutes=5):
                return self._token

        # Generate new token
        try:
            from databricks.sdk import WorkspaceClient

            w = WorkspaceClient()
            cred = w.database.generate_database_credential(
                request_id=str(uuid.uuid4()),
                instance_names=[self._instance_name]
            )

            self._token = cred.token
            # Tokens expire in 1 hour, but we refresh at 55 minutes
            self._token_expiry = datetime.now() + timedelta(minutes=55)

            logger.info(f"Generated new Lakebase OAuth token for instance: {self._instance_name}")
            return self._token

        except ImportError:
            raise RuntimeError(
                "databricks-sdk is required for OAuth authentication. "
                "Install with: pip install databricks-sdk>=0.56.0"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to generate Lakebase OAuth token: {e}")

    def get_connection_string(
        self,
        host: str,
        database: str,
        user: str,
        port: int = 5432
    ) -> str:
        """Get a connection string with fresh OAuth token as password.

        Args:
            host: Lakebase instance hostname
            database: Database name
            user: Databricks user email
            port: PostgreSQL port (default: 5432)

        Returns:
            PostgreSQL connection string with OAuth token
        """
        token = self.get_token()
        return (
            f"postgresql://{user}:{token}@{host}:{port}/{database}?sslmode=require"
        )

    def clear_token(self) -> None:
        """Clear cached token (e.g., on authentication failure)."""
        self._token = None
        self._token_expiry = None

    @property
    def is_configured(self) -> bool:
        """Check if the auth manager is configured."""
        return self._instance_name is not None

    @property
    def token_expires_at(self) -> Optional[datetime]:
        """Get token expiry time (for monitoring)."""
        return self._token_expiry


# Singleton instance
lakebase_auth = LakebaseAuthManager()
