"""
Legacy Databricks Service - Deprecated in favor of new clean architecture
This file is kept for backward compatibility but should not be used in new code.
Use the services in app.services.* and DALs in app.dal.* instead.
"""
from typing import List, Optional
from app.services.catalog_service import catalog_service
from app.core.databricks_client import databricks_manager
import logging

logger = logging.getLogger(__name__)


class DatabricksService:
    """Legacy service - use catalog_service and comment_service instead"""
    
    def __init__(self):
        """Initialize with deprecation warning"""
        logger.warning("DatabricksService is deprecated. Use catalog_service and comment_service instead.")
        self.catalog_service = catalog_service
        self.databricks_manager = databricks_manager
    
    async def test_connection(self) -> bool:
        """Test the Databricks connection - delegates to new architecture"""
        try:
            return await self.databricks_manager.test_connections()
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Singleton instance
databricks_service = DatabricksService()