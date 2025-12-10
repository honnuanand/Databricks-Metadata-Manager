"""
Databricks client configuration following tariffs project pattern
"""
from typing import Optional, Dict, Any
from databricks import sql as databricks_sql
from databricks.sdk import WorkspaceClient
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class DatabricksConfig:
    """Databricks configuration for both SDK and SQL connections"""

    def __init__(self):
        import os

        # Extract hostname from DATABRICKS_HOST (remove https:// prefix)
        databricks_host = settings.DATABRICKS_HOST
        if not databricks_host:
            raise ValueError("DATABRICKS_HOST environment variable must be set")
        self.server_hostname = databricks_host.replace("https://", "").replace("http://", "")

        # Use warehouse path from environment variable, with fallback for backwards compatibility
        self.http_path = settings.DATABRICKS_WAREHOUSE_PATH or "/sql/1.0/warehouses/00887ae543d50e2a"

        # Check if running in Databricks Apps with OAuth
        self.has_oauth = bool(os.getenv('DATABRICKS_CLIENT_ID') and os.getenv('DATABRICKS_CLIENT_SECRET'))

        # Token is optional when running with OAuth in Databricks Apps
        self.access_token = settings.DATABRICKS_TOKEN
        if not self.access_token and not self.has_oauth:
            raise ValueError("DATABRICKS_TOKEN environment variable must be set (or run in Databricks Apps with OAuth)")

        # Catalog and schema - can be made configurable if needed
        self.catalog = "arao"
        self.schema = "metadata_manager"

        logger.info(f"DatabricksConfig: server_hostname = {self.server_hostname}")
        if self.has_oauth:
            logger.info("DatabricksConfig: OAuth credentials detected (Databricks Apps)")
        elif self.access_token:
            logger.info("DatabricksConfig: Using DATABRICKS_TOKEN from environment")
    
    def get_sql_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters for databricks.sql connector

        Prefer OAuth when running in Databricks Apps (service principal auth).
        Fall back to PAT token if OAuth not available.
        """
        params = {
            "server_hostname": self.server_hostname,
            "http_path": self.http_path,
        }
        # Prefer OAuth when running in Databricks Apps
        if self.has_oauth:
            logger.info("SQL connection using OAuth (Databricks Apps service principal)")
            # Don't include access_token - let connector use OAuth from environment
        elif self.access_token:
            params["access_token"] = self.access_token
            logger.info("SQL connection using PAT token authentication")
        else:
            logger.info("SQL connection: no auth configured")
        return params
    
    def get_workspace_client(self) -> WorkspaceClient:
        """Get WorkspaceClient for catalog operations

        Always uses PAT token when available (preferred for catalog operations).
        Falls back to OAuth only if no token is provided.
        """
        import os

        if self.access_token:
            logger.info("DatabricksConfig: Using PAT token authentication")
            # Clear OAuth environment variables to prevent SDK auto-detection conflict
            # The SDK will see both OAuth and PAT if we don't clear these
            oauth_client_id = os.environ.pop('DATABRICKS_CLIENT_ID', None)
            oauth_client_secret = os.environ.pop('DATABRICKS_CLIENT_SECRET', None)
            if oauth_client_id:
                logger.info("DatabricksConfig: Cleared DATABRICKS_CLIENT_ID to avoid OAuth/PAT conflict")

            return WorkspaceClient(
                host=f"https://{self.server_hostname}",
                token=self.access_token
            )
        elif self.has_oauth:
            logger.info("DatabricksConfig: Using OAuth authentication (Databricks Apps)")
            # When no token but OAuth credentials are present, let SDK use OAuth
            return WorkspaceClient(
                host=f"https://{self.server_hostname}"
            )
        else:
            logger.warning("DatabricksConfig: No authentication configured!")
            return WorkspaceClient(
                host=f"https://{self.server_hostname}"
            )


class DatabricksConnectionManager:
    """Manages Databricks connections following the tariffs project pattern"""

    def __init__(self):
        self._config: Optional[DatabricksConfig] = None
        self._workspace_client: Optional[WorkspaceClient] = None

    @property
    def config(self) -> DatabricksConfig:
        """Lazy-load config to ensure environment variables are loaded"""
        if self._config is None:
            self._config = DatabricksConfig()
        return self._config
    
    @property
    def workspace_client(self) -> WorkspaceClient:
        """Get or create workspace client"""
        if self._workspace_client is None:
            self._workspace_client = self.config.get_workspace_client()
        return self._workspace_client
    
    def get_sql_connection(self):
        """Get databricks.sql connection for SQL operations"""
        return databricks_sql.connect(**self.config.get_sql_connection_params())
    
    async def test_connections(self) -> Dict[str, bool]:
        """Test both workspace and SQL connections"""
        results = {"workspace": False, "sql": False}
        
        # Test workspace connection
        try:
            catalogs = list(self.workspace_client.catalogs.list())
            results["workspace"] = True
            logger.info(f"Workspace connection successful. Found {len(catalogs)} catalogs.")
        except Exception as e:
            logger.error(f"Workspace connection failed: {e}")
        
        # Test SQL connection
        try:
            with self.get_sql_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT CURRENT_USER()")
                    result = cursor.fetchone()
                    if result:
                        results["sql"] = True
                        logger.info(f"SQL connection successful. Current user: {result[0]}")
        except Exception as e:
            logger.error(f"SQL connection failed: {e}")
        
        return results


# Global instance
databricks_manager = DatabricksConnectionManager()