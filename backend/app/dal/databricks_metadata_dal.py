"""
Data Access Layer for Databricks metadata operations
Uses SQL queries via databricks-sql-connector (like text2sql app)
"""
from typing import List, Optional, Dict, Any
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
    """Data Access Layer for Databricks metadata operations using SQL queries"""

    def __init__(self):
        logger.info("="*80)
        logger.info("DatabricksMetadataDAL initializing (SQL mode)...")

        # Log config details
        config = databricks_manager.config
        logger.info(f"Config - Hostname: {config.server_hostname}")
        logger.info(f"Config - HTTP Path: {config.http_path}")
        if config.has_oauth:
            logger.info(f"Config - Auth: OAuth (Databricks Apps)")
        elif config.access_token:
            logger.info(f"Config - Auth: PAT token ({config.access_token[:20]}...)")
        else:
            logger.info(f"Config - Auth: None configured")
        logger.info(f"Config - Catalog: {config.catalog}")
        logger.info(f"Config - Schema: {config.schema}")
        logger.info("DatabricksMetadataDAL initialized successfully (SQL mode)")
        logger.info("="*80)

    def _get_connection(self):
        """Get SQL connection from manager"""
        return databricks_manager.get_sql_connection()

    async def list_catalogs(self) -> List[CatalogSchema]:
        """List all accessible catalogs using SHOW CATALOGS"""
        try:
            logger.info("list_catalogs: Starting catalog listing via SQL...")

            with self._get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SHOW CATALOGS")
                    rows = cursor.fetchall()

            result = []
            for row in rows:
                catalog_name = row[0] if row else None
                if catalog_name:
                    result.append(CatalogSchema(
                        name=catalog_name,
                        comment=None,
                        owner=None,
                        created_at=None,
                        updated_at=None,
                        schema_count=0
                    ))

            logger.info(f"Retrieved {len(result)} catalogs via SQL")
            return result
        except Exception as e:
            logger.error(f"Error listing catalogs via SQL: {type(e).__name__}: {e}", exc_info=True)
            raise

    async def list_schemas(self, catalog_name: str) -> List[SchemaSchema]:
        """List all schemas in a catalog using SHOW SCHEMAS"""
        try:
            logger.info(f"list_schemas: Listing schemas in '{catalog_name}' via SQL...")

            with self._get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(f"SHOW SCHEMAS IN `{catalog_name}`")
                    rows = cursor.fetchall()

            result = []
            for row in rows:
                schema_name = row[0] if row else None
                if schema_name:
                    result.append(SchemaSchema(
                        catalog_name=catalog_name,
                        name=schema_name,
                        full_name=f"{catalog_name}.{schema_name}",
                        comment=None,
                        owner=None,
                        created_at=None,
                        updated_at=None,
                        table_count=0
                    ))

            logger.info(f"Retrieved {len(result)} schemas for catalog {catalog_name}")
            return result
        except Exception as e:
            logger.error(f"Error listing schemas for catalog {catalog_name}: {e}")
            raise

    async def list_tables(self, catalog_name: str, schema_name: str) -> List[TableSchema]:
        """List all tables in a schema using SHOW TABLES"""
        try:
            logger.info(f"list_tables: Listing tables in '{catalog_name}.{schema_name}' via SQL...")

            with self._get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(f"SHOW TABLES IN `{catalog_name}`.`{schema_name}`")
                    rows = cursor.fetchall()

            result = []
            for row in rows:
                # SHOW TABLES returns: database, tableName, isTemporary
                table_name = row[1] if len(row) > 1 else row[0]
                if table_name:
                    result.append(TableSchema(
                        catalog_name=catalog_name,
                        schema_name=schema_name,
                        name=table_name,
                        full_name=f"{catalog_name}.{schema_name}.{table_name}",
                        table_type="TABLE",
                        comment=None,
                        owner=None,
                        created_at=None,
                        updated_at=None
                    ))

            logger.info(f"Retrieved {len(result)} tables for {catalog_name}.{schema_name}")
            return result
        except Exception as e:
            logger.error(f"Error listing tables for {catalog_name}.{schema_name}: {e}")
            raise

    async def get_table_columns(self, catalog_name: str, schema_name: str, table_name: str) -> List[ColumnSchema]:
        """Get all columns for a table using DESCRIBE TABLE"""
        try:
            logger.info(f"get_table_columns: Describing '{catalog_name}.{schema_name}.{table_name}' via SQL...")

            with self._get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(f"DESCRIBE TABLE `{catalog_name}`.`{schema_name}`.`{table_name}`")
                    rows = cursor.fetchall()

            result = []
            for idx, row in enumerate(rows):
                # DESCRIBE TABLE returns: col_name, data_type, comment
                col_name = row[0] if len(row) > 0 else None
                data_type = row[1] if len(row) > 1 else "STRING"
                comment = row[2] if len(row) > 2 else None

                # Skip partition info rows (they start with # or are empty)
                if col_name and not col_name.startswith('#') and col_name.strip():
                    result.append(ColumnSchema(
                        catalog_name=catalog_name,
                        schema_name=schema_name,
                        table_name=table_name,
                        name=col_name,
                        full_name=f"{catalog_name}.{schema_name}.{table_name}.{col_name}",
                        data_type=data_type,
                        comment=comment,
                        nullable=True,
                        partition_index=None,
                        position=idx
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
