"""
Catalog Service - Business logic for Databricks catalog operations
"""
from typing import List, Optional
from app.dal.databricks_metadata_dal import databricks_metadata_dal
from app.dal.application_data_dal import application_data_dal
from app.schemas.databricks import CatalogInfo, SchemaInfo, TableInfo, ColumnInfo
import logging

logger = logging.getLogger(__name__)


class CatalogService:
    """Service for catalog exploration and metadata operations"""
    
    def __init__(self):
        self.metadata_dal = databricks_metadata_dal
        self.app_dal = application_data_dal
    
    async def list_accessible_catalogs(self, user_id: str) -> List[CatalogInfo]:
        """List catalogs accessible to the user"""
        try:
            # Log user activity
            await self.app_dal.log_audit_event(
                user_id=user_id,
                action="list_catalogs",
                entity_type="catalog"
            )
            
            catalogs = await self.metadata_dal.list_catalogs()
            logger.info(f"User {user_id} accessed {len(catalogs)} catalogs")
            return catalogs
        except Exception as e:
            logger.error(f"Error listing catalogs for user {user_id}: {e}")
            raise
    
    async def list_schemas_in_catalog(self, catalog_name: str, user_id: str) -> List[SchemaInfo]:
        """List schemas in a specific catalog"""
        try:
            # Log user activity
            await self.app_dal.log_audit_event(
                user_id=user_id,
                action="list_schemas",
                entity_type="schema",
                entity_path=catalog_name
            )
            
            schemas = await self.metadata_dal.list_schemas(catalog_name)
            logger.info(f"User {user_id} accessed {len(schemas)} schemas in catalog {catalog_name}")
            return schemas
        except Exception as e:
            logger.error(f"Error listing schemas in catalog {catalog_name} for user {user_id}: {e}")
            raise
    
    async def list_tables_in_schema(self, catalog_name: str, schema_name: str, user_id: str) -> List[TableInfo]:
        """List tables in a specific schema"""
        try:
            # Log user activity
            await self.app_dal.log_audit_event(
                user_id=user_id,
                action="list_tables",
                entity_type="table",
                entity_path=f"{catalog_name}.{schema_name}"
            )
            
            tables = await self.metadata_dal.list_tables(catalog_name, schema_name)
            logger.info(f"User {user_id} accessed {len(tables)} tables in {catalog_name}.{schema_name}")
            return tables
        except Exception as e:
            logger.error(f"Error listing tables in {catalog_name}.{schema_name} for user {user_id}: {e}")
            raise
    
    async def get_table_columns(self, catalog_name: str, schema_name: str, table_name: str, user_id: str) -> List[ColumnInfo]:
        """Get columns for a specific table"""
        try:
            # Log user activity
            await self.app_dal.log_audit_event(
                user_id=user_id,
                action="get_columns",
                entity_type="column",
                entity_path=f"{catalog_name}.{schema_name}.{table_name}"
            )
            
            columns = await self.metadata_dal.get_table_columns(catalog_name, schema_name, table_name)
            logger.info(f"User {user_id} accessed {len(columns)} columns for {catalog_name}.{schema_name}.{table_name}")
            return columns
        except Exception as e:
            logger.error(f"Error getting columns for {catalog_name}.{schema_name}.{table_name} for user {user_id}: {e}")
            raise
    
    async def search_entities(self, query: str, entity_types: List[str], user_id: str) -> dict:
        """Search for entities across catalogs (simplified implementation)"""
        try:
            # Log search activity
            await self.app_dal.log_audit_event(
                user_id=user_id,
                action="search_entities",
                details=f"Query: {query}, Types: {', '.join(entity_types)}"
            )
            
            results = {
                "catalogs": [],
                "schemas": [],
                "tables": [],
                "columns": []
            }
            
            # For now, implement a basic search across all catalogs
            # In a real implementation, this would be more efficient with proper indexing
            if "catalog" in entity_types:
                catalogs = await self.metadata_dal.list_catalogs()
                results["catalogs"] = [
                    catalog for catalog in catalogs 
                    if query.lower() in catalog.name.lower() or 
                       (catalog.comment and query.lower() in catalog.comment.lower())
                ]
            
            # Similar logic for schemas, tables, and columns would follow
            logger.info(f"User {user_id} searched for '{query}' across {entity_types}")
            return results
        except Exception as e:
            logger.error(f"Error searching entities for user {user_id}: {e}")
            raise


# Singleton instance
catalog_service = CatalogService()