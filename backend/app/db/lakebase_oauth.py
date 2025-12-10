"""
Lakebase OAuth Token Manager for passwordless PostgreSQL connections.

This module manages OAuth tokens for connecting to Databricks Lakebase
using service principal credentials instead of static passwords.
Tokens are automatically refreshed before expiry.
"""
import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from threading import Lock

logger = logging.getLogger(__name__)


class LakebaseOAuthManager:
    """
    Manages OAuth tokens for Lakebase connections with automatic refresh.

    Tokens expire after 1 hour, so we refresh proactively (5 minutes before expiry).
    This class is thread-safe for use in multi-threaded web applications.
    """

    def __init__(
        self,
        lakebase_instance: str,
        lakebase_host: str,
        databricks_host: Optional[str] = None,
        refresh_buffer_seconds: int = 300
    ):
        """
        Initialize the OAuth manager.

        Args:
            lakebase_instance: The Lakebase instance name (e.g., "arao-lb")
            lakebase_host: The PostgreSQL hostname (e.g., "instance-xxx.database.cloud.databricks.com")
            databricks_host: Optional Databricks workspace URL (auto-detected from env if not provided)
            refresh_buffer_seconds: Seconds before expiry to trigger refresh (default 5 minutes)
        """
        self.lakebase_instance = lakebase_instance
        self.lakebase_host = lakebase_host
        self.databricks_host = databricks_host or os.environ.get("DATABRICKS_HOST")
        self.refresh_buffer_seconds = refresh_buffer_seconds

        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._username: Optional[str] = None
        self._workspace_client = None
        self._lock = Lock()

        # Check if OAuth credentials are available
        self._has_oauth = bool(
            os.environ.get('DATABRICKS_CLIENT_ID') and
            os.environ.get('DATABRICKS_CLIENT_SECRET')
        )

        if self._has_oauth:
            logger.info("LakebaseOAuthManager: OAuth credentials detected (SP mode)")
        else:
            logger.info("LakebaseOAuthManager: No OAuth credentials, will use PAT token if available")

    @property
    def is_oauth_available(self) -> bool:
        """Check if OAuth authentication is available"""
        return self._has_oauth

    def _get_workspace_client(self):
        """Get or create WorkspaceClient (lazy initialization)"""
        if self._workspace_client is None:
            from databricks.sdk import WorkspaceClient

            if self._has_oauth:
                # Let SDK auto-discover OAuth credentials from environment
                logger.info("LakebaseOAuthManager: Creating WorkspaceClient with OAuth")
                self._workspace_client = WorkspaceClient(host=self.databricks_host)
            else:
                # Use PAT token if available
                token = os.environ.get('DATABRICKS_TOKEN')
                if token:
                    logger.info("LakebaseOAuthManager: Creating WorkspaceClient with PAT token")
                    self._workspace_client = WorkspaceClient(
                        host=self.databricks_host,
                        token=token
                    )
                else:
                    raise ValueError("No OAuth credentials or PAT token available")

        return self._workspace_client

    def _generate_token(self) -> Tuple[str, datetime]:
        """Generate a new OAuth token for Lakebase"""
        w = self._get_workspace_client()

        logger.info(f"LakebaseOAuthManager: Generating token for instance '{self.lakebase_instance}'")

        cred = w.database.generate_database_credential(
            request_id=str(uuid.uuid4()),
            instance_names=[self.lakebase_instance]
        )

        # Parse expiration time
        expiry = None
        if hasattr(cred, 'expiration_time') and cred.expiration_time:
            try:
                if isinstance(cred.expiration_time, (int, float)):
                    expiry = datetime.fromtimestamp(cred.expiration_time / 1000, tz=timezone.utc)
                else:
                    expiry = datetime.fromisoformat(str(cred.expiration_time).replace('Z', '+00:00'))
            except Exception as e:
                logger.warning(f"Could not parse expiration_time: {e}")
                expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        else:
            # Default to 1 hour from now
            expiry = datetime.now(timezone.utc) + timedelta(hours=1)

        logger.info(f"LakebaseOAuthManager: Token generated, expires at {expiry.isoformat()}")
        return cred.token, expiry

    def get_token(self) -> str:
        """
        Get a valid OAuth token, refreshing if needed.

        This method is thread-safe.

        Returns:
            A valid OAuth token string
        """
        with self._lock:
            now = datetime.now(timezone.utc)

            # Check if we need to refresh
            needs_refresh = (
                self._token is None or
                self._token_expiry is None or
                (self._token_expiry - now).total_seconds() < self.refresh_buffer_seconds
            )

            if needs_refresh:
                logger.info(f"LakebaseOAuthManager: Refreshing token (current expires in {self.token_expires_in}s)")
                self._token, self._token_expiry = self._generate_token()

            return self._token

    def get_username(self) -> str:
        """
        Get the username for PostgreSQL connection.

        For service principal OAuth, this is the client_id.
        For user OAuth, this is the user's email.

        Returns:
            Username string for PostgreSQL connection
        """
        if self._username is None:
            if self._has_oauth:
                # For SP, username is the client_id
                self._username = os.environ.get('DATABRICKS_CLIENT_ID')
                logger.info(f"LakebaseOAuthManager: Using SP client_id as username")
            else:
                # For user auth, get from workspace client
                w = self._get_workspace_client()
                self._username = w.current_user.me().user_name
                logger.info(f"LakebaseOAuthManager: Using user email as username: {self._username}")

        return self._username

    def get_connection_params(self) -> dict:
        """
        Get PostgreSQL connection parameters with fresh token.

        Returns:
            Dict with host, port, database, user, password, sslmode
        """
        return {
            "host": self.lakebase_host,
            "port": 5432,
            "database": "databricks_postgres",
            "user": self.get_username(),
            "password": self.get_token(),
            "sslmode": "require"
        }

    def get_database_url(self) -> str:
        """
        Get a DATABASE_URL string with fresh token.

        Returns:
            PostgreSQL connection URL string
        """
        from urllib.parse import quote_plus

        token = self.get_token()
        username = self.get_username()

        return (
            f"postgresql://{quote_plus(username)}:{quote_plus(token)}"
            f"@{self.lakebase_host}:5432/databricks_postgres?sslmode=require"
        )

    @property
    def token_expires_in(self) -> Optional[int]:
        """Get seconds until token expires"""
        if self._token_expiry is None:
            return None
        return int((self._token_expiry - datetime.now(timezone.utc)).total_seconds())


# Global singleton instance (initialized lazily)
_oauth_manager: Optional[LakebaseOAuthManager] = None
_oauth_manager_lock = Lock()


def get_lakebase_oauth_manager() -> Optional[LakebaseOAuthManager]:
    """
    Get or create the global LakebaseOAuthManager instance.

    Returns None if OAuth is not configured (falls back to static credentials).

    Configuration is read from environment variables:
    - LAKEBASE_INSTANCE: The Lakebase instance name
    - LAKEBASE_HOST: The PostgreSQL hostname
    - DATABRICKS_HOST: The Databricks workspace URL
    - DATABRICKS_CLIENT_ID: Service principal client ID (for OAuth)
    - DATABRICKS_CLIENT_SECRET: Service principal secret (for OAuth)
    """
    global _oauth_manager

    with _oauth_manager_lock:
        if _oauth_manager is None:
            lakebase_instance = os.environ.get('LAKEBASE_INSTANCE')
            lakebase_host = os.environ.get('LAKEBASE_HOST')

            if not lakebase_instance or not lakebase_host:
                logger.info("LakebaseOAuthManager: LAKEBASE_INSTANCE or LAKEBASE_HOST not set, OAuth disabled")
                return None

            # Check if OAuth credentials are available
            has_oauth = bool(
                os.environ.get('DATABRICKS_CLIENT_ID') and
                os.environ.get('DATABRICKS_CLIENT_SECRET')
            )

            if not has_oauth:
                logger.info("LakebaseOAuthManager: No OAuth credentials, using static DATABASE_URL")
                return None

            _oauth_manager = LakebaseOAuthManager(
                lakebase_instance=lakebase_instance,
                lakebase_host=lakebase_host
            )
            logger.info("LakebaseOAuthManager: Initialized global instance")

        return _oauth_manager
