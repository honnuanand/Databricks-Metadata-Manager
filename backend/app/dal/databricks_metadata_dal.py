"""
Data Access Layer for Databricks metadata operations
"""
from typing import List, Optional, Dict, Any
from databricks.sdk.service.catalog import CatalogInfo, SchemaInfo, TableInfo
from app.core.databricks_client import databricks_manager
from app.schemas.databricks import (
    CatalogInfo as CatalogSchema,
    SchemaInfo as SchemaSchema,
    TableInfo as TableSchema,
    ColumnInfo as ColumnSchema
)
import logging

logger = logging.getLogger(__name__)


class DatabricksMetadataDAL:
    """Data Access Layer for Databricks metadata operations"""

    def __init__(self):
        logger.info("="*80)
        logger.info("DatabricksMetadataDAL initializing...")

        # Log config details before creating client
        config = databricks_manager.config
        logger.info(f"Config - Hostname: {config.server_hostname}")
        logger.info(f"Config - Token: {config.access_token[:20]}...")
        logger.info(f"Config - Catalog: {config.catalog}")
        logger.info(f"Config - Schema: {config.schema}")

        self.client = databricks_manager.workspace_client
        self.sql_connection_params = databricks_manager.config.get_sql_connection_params()
        logger.info("DatabricksMetadataDAL initialized successfully")
        logger.info("="*80)
    
    async def list_catalogs(self) -> List[CatalogSchema]:
        """List all accessible catalogs"""
        try:
            logger.info("list_catalogs: Starting catalog listing...")
            logger.info(f"list_catalogs: Using workspace client for host: {databricks_manager.config.server_hostname}")

            catalogs = self.client.catalogs.list()
            result = []
            for catalog in catalogs:
                result.append(CatalogSchema(
                    name=catalog.name,
                    comment=catalog.comment,
                    owner=catalog.owner,
                    created_at=str(catalog.created_at) if catalog.created_at else None,
                    updated_at=str(catalog.updated_at) if catalog.updated_at else None,
                    schema_count=0  # Will be calculated from fetched schemas
                ))
            logger.info(f"Retrieved {len(result)} catalogs successfully")
            return result
        except Exception as e:
            logger.error(f"Error listing catalogs: {type(e).__name__}: {e}", exc_info=True)
            raise
    
    async def list_schemas(self, catalog_name: str) -> List[SchemaSchema]:
        """List all schemas in a catalog"""
        try:
            schemas = self.client.schemas.list(catalog_name=catalog_name)
            result = []
            for schema in schemas:
                result.append(SchemaSchema(
                    catalog_name=catalog_name,
                    name=schema.name,
                    full_name=f"{catalog_name}.{schema.name}",
                    comment=schema.comment,
                    owner=schema.owner,
                    created_at=str(schema.created_at) if schema.created_at else None,
                    updated_at=str(schema.updated_at) if schema.updated_at else None,
                    table_count=0  # Will be calculated from fetched tables
                ))
            logger.info(f"Retrieved {len(result)} schemas for catalog {catalog_name}")
            return result
        except Exception as e:
            logger.error(f"Error listing schemas for catalog {catalog_name}: {e}")
            raise
    
    async def list_tables(self, catalog_name: str, schema_name: str) -> List[TableSchema]:
        """List all tables in a schema"""
        try:
            tables = self.client.tables.list(
                catalog_name=catalog_name,
                schema_name=schema_name
            )
            result = []
            for table in tables:
                result.append(TableSchema(
                    catalog_name=catalog_name,
                    schema_name=schema_name,
                    name=table.name,
                    full_name=f"{catalog_name}.{schema_name}.{table.name}",
                    table_type=table.table_type.value if table.table_type else None,
                    comment=table.comment,
                    owner=table.owner,
                    created_at=str(table.created_at) if table.created_at else None,
                    updated_at=str(table.updated_at) if table.updated_at else None
                ))
            logger.info(f"Retrieved {len(result)} tables for {catalog_name}.{schema_name}")
            return result
        except Exception as e:
            logger.error(f"Error listing tables for {catalog_name}.{schema_name}: {e}")
            raise
    
    async def get_table_columns(self, catalog_name: str, schema_name: str, table_name: str) -> List[ColumnSchema]:
        """Get all columns for a table"""
        try:
            table = self.client.tables.get(
                full_name=f"{catalog_name}.{schema_name}.{table_name}"
            )
            
            if not table.columns:
                return []
            
            result = []
            for idx, column in enumerate(table.columns):
                result.append(ColumnSchema(
                    catalog_name=catalog_name,
                    schema_name=schema_name,
                    table_name=table_name,
                    name=column.name,
                    full_name=f"{catalog_name}.{schema_name}.{table_name}.{column.name}",
                    data_type=column.type_text or column.type_name.value,
                    comment=column.comment,
                    nullable=column.nullable if column.nullable is not None else True,
                    partition_index=column.partition_index,
                    position=column.position or idx
                ))
            logger.info(f"Retrieved {len(result)} columns for {catalog_name}.{schema_name}.{table_name}")
            return result
        except Exception as e:
            logger.error(f"Error getting columns for {catalog_name}.{schema_name}.{table_name}: {e}")
            raise
    
    async def update_comment(self, entity_type: str, entity_path: Dict[str, str], comment: str) -> bool:
        """Update comment for a catalog entity using SQL"""
        try:
            sql_statement = self._build_comment_sql(entity_type, entity_path, comment)
            
            # Use databricks.sql connection for SQL operations
            with databricks_manager.get_sql_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql_statement)
            
            logger.info(f"Successfully updated comment for {entity_type}: {entity_path}")
            return True
        except Exception as e:
            logger.error(f"Error updating comment for {entity_type} {entity_path}: {e}")
            raise
    
    def _build_comment_sql(self, entity_type: str, entity_path: Dict[str, str], comment: str) -> str:
        """Build SQL statement for updating comments"""
        # Escape single quotes in comment
        comment_escaped = comment.replace("'", "''")
        
        if entity_type == "catalog":
            return f"COMMENT ON CATALOG {entity_path['catalog']} IS '{comment_escaped}'"
        
        elif entity_type == "schema":
            return f"COMMENT ON SCHEMA {entity_path['catalog']}.{entity_path['schema']} IS '{comment_escaped}'"
        
        elif entity_type == "table":
            return f"""
            ALTER TABLE {entity_path['catalog']}.{entity_path['schema']}.{entity_path['table']}
            SET TBLPROPERTIES ('comment' = '{comment_escaped}')
            """
        
        elif entity_type == "column":
            return f"""
            ALTER TABLE {entity_path['catalog']}.{entity_path['schema']}.{entity_path['table']}
            ALTER COLUMN {entity_path['column']}
            COMMENT '{comment_escaped}'
            """
        
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")
    
    async def test_connection(self) -> bool:
        """Test the Databricks connection"""
        try:
            # Try to list catalogs as a simple connectivity test
            catalogs = list(self.client.catalogs.list())
            logger.info(f"Connection test successful. Found {len(catalogs)} catalogs.")
            return True
        except Exception as e:
            logger.error(f"Databricks connection test failed: {e}")
            return False


# Singleton instance
databricks_metadata_dal = DatabricksMetadataDAL()