from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.schemas.databricks import (
    CatalogInfo,
    SchemaInfo,
    TableInfo,
    ColumnInfo,
    CatalogsResponse,
    CatalogResponse,
    SchemasResponse,
    TablesResponse,
    ColumnsResponse
)
from app.services.catalog_service import catalog_service
from app.api.dependencies.auth import get_current_active_user
from app.schemas.user import User
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/debug-config")
async def debug_databricks_config():
    """Debug endpoint to check Databricks configuration and identify service principal"""
    try:
        from app.core.databricks_client import databricks_manager
        from app.core.config import settings

        config = databricks_manager.config

        # Try to get current_user from SQL connection
        current_user = None
        try:
            with databricks_manager.get_sql_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT current_user()")
                    result = cursor.fetchone()
                    if result:
                        current_user = result[0]
        except Exception as sql_error:
            current_user = f"Error: {str(sql_error)}"

        return {
            "status": "success",
            "config": {
                "server_hostname": config.server_hostname,
                "catalog": config.catalog,
                "schema": config.schema,
                "token_prefix": config.access_token[:20] if config.access_token else "NOT SET",
                "settings_host": settings.DATABRICKS_HOST,
                "settings_token_set": bool(settings.DATABRICKS_TOKEN),
                "settings_token_prefix": settings.DATABRICKS_TOKEN[:20] if settings.DATABRICKS_TOKEN else "NOT SET",
            },
            "service_principal": {
                "current_user_sql": current_user,
                "instructions": "Use this value in GRANT statements: GRANT USE CATALOG ON CATALOG arao TO `<current_user_sql>`"
            }
        }
    except Exception as e:
        logger.error(f"Error in debug-config: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "type": type(e).__name__
        }


@router.get("/", response_model=CatalogsResponse)
async def list_catalogs(
    search: Optional[str] = Query(None, description="Search term for catalog names"),
    current_user: User = Depends(get_current_active_user)
):
    """List all accessible catalogs"""
    try:
        logger.info("="*80)
        logger.info("🔍 BROWSE CATALOG: Starting catalog list request")
        logger.info(f"   User: {current_user.username} (ID: {current_user.user_id})")
        logger.info(f"   Search filter: {search or 'None'}")

        # Check what workspace we're connecting to
        from app.core.databricks_client import databricks_manager
        config = databricks_manager.config
        logger.info(f"   📍 Workspace: {config.server_hostname}")
        logger.info(f"   📦 Default Catalog: {config.catalog}")
        logger.info(f"   📂 Default Schema: {config.schema}")
        logger.info(f"   🔑 Token: {config.access_token[:20]}...")

        logger.info("   Calling catalog_service.list_accessible_catalogs()...")
        catalogs = await catalog_service.list_accessible_catalogs(current_user.user_id)

        logger.info(f"   ✅ Retrieved {len(catalogs)} catalogs:")
        for cat in catalogs:
            logger.info(f"      - {cat.name} (owner: {cat.owner})")

        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            original_count = len(catalogs)
            catalogs = [c for c in catalogs if search_lower in c.name.lower() or
                       (c.comment and search_lower in c.comment.lower())]
            logger.info(f"   🔍 Search filter '{search}' reduced from {original_count} to {len(catalogs)} catalogs")

        logger.info(f"   📤 Returning {len(catalogs)} catalogs to client")
        logger.info("="*80)
        return CatalogsResponse(catalogs=catalogs)
    except Exception as e:
        logger.error(f"❌ Error listing catalogs for user {current_user.username}: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list catalogs: {str(e)}"
        )


@router.get("/{catalog_name}", response_model=CatalogResponse)
async def get_catalog(
    catalog_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get details of a specific catalog"""
    try:
        logger.info("="*80)
        logger.info(f"🔍 GET CATALOG: Fetching details for catalog '{catalog_name}'")
        logger.info(f"   User: {current_user.username} (ID: {current_user.user_id})")

        # Get all catalogs and find the requested one
        catalogs = await catalog_service.list_accessible_catalogs(current_user.user_id)
        catalog = next((c for c in catalogs if c.name == catalog_name), None)

        if not catalog:
            logger.warning(f"   ❌ Catalog '{catalog_name}' not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Catalog '{catalog_name}' not found"
            )

        logger.info(f"   ✅ Found catalog: {catalog.name} (owner: {catalog.owner})")
        logger.info("="*80)
        return CatalogResponse(catalog=catalog)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting catalog {catalog_name}: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get catalog {catalog_name}: {str(e)}"
        )


@router.get("/{catalog_name}/schemas", response_model=SchemasResponse)
async def list_schemas(
    catalog_name: str,
    search: Optional[str] = Query(None, description="Search term for schema names"),
    current_user: User = Depends(get_current_active_user)
):
    """List all schemas in a catalog"""
    try:
        logger.info("="*80)
        logger.info(f"🔍 BROWSE SCHEMAS: Listing schemas in catalog '{catalog_name}'")
        logger.info(f"   User: {current_user.username} (ID: {current_user.user_id})")
        logger.info(f"   Search filter: {search or 'None'}")

        # Check if this is the arao catalog
        if catalog_name == "arao":
            logger.info(f"   ✅ Accessing ARAO catalog - expecting metadata_manager and metadata_test schemas")
        else:
            logger.info(f"   ⚠️  Accessing catalog '{catalog_name}' (not arao)")

        logger.info(f"   Calling catalog_service.list_schemas_in_catalog('{catalog_name}')...")
        schemas = await catalog_service.list_schemas_in_catalog(catalog_name, current_user.user_id)

        logger.info(f"   ✅ Retrieved {len(schemas)} schemas in '{catalog_name}':")
        for schema in schemas:
            logger.info(f"      - {schema.name} (full: {schema.full_name})")
            if schema.name in ["metadata_manager", "metadata_test"]:
                logger.info(f"        🎯 Found target schema: {schema.name}")

        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            original_count = len(schemas)
            schemas = [s for s in schemas if search_lower in s.name.lower() or
                      (s.comment and search_lower in s.comment.lower())]
            logger.info(f"   🔍 Search filter '{search}' reduced from {original_count} to {len(schemas)} schemas")

        logger.info(f"   📤 Returning {len(schemas)} schemas to client")
        logger.info("="*80)
        return SchemasResponse(schemas=schemas)
    except Exception as e:
        logger.error(f"❌ Error listing schemas for catalog {catalog_name}: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list schemas in catalog {catalog_name}: {str(e)}"
        )


@router.get("/{catalog_name}/{schema_name}/tables", response_model=TablesResponse)
async def list_tables(
    catalog_name: str,
    schema_name: str,
    search: Optional[str] = Query(None, description="Search term for table names"),
    table_type: Optional[str] = Query(None, description="Filter by table type"),
    current_user: User = Depends(get_current_active_user)
):
    """List all tables in a schema"""
    try:
        logger.info("="*80)
        logger.info(f"🔍 BROWSE TABLES: Listing tables in {catalog_name}.{schema_name}")
        logger.info(f"   User: {current_user.username} (ID: {current_user.user_id})")
        logger.info(f"   Search filter: {search or 'None'}")
        logger.info(f"   Table type filter: {table_type or 'None'}")

        # Check if this is one of our target schemas
        if catalog_name == "arao" and schema_name in ["metadata_manager", "metadata_test"]:
            logger.info(f"   🎯 Accessing target schema: {catalog_name}.{schema_name}")
            if schema_name == "metadata_manager":
                logger.info(f"      Expected tables: users, comment_suggestions, approvals, audit_logs")
            elif schema_name == "metadata_test":
                logger.info(f"      Expected tables: users, products, orders, order_items, employees, etc.")
        else:
            logger.info(f"   ℹ️  Accessing schema: {catalog_name}.{schema_name}")

        logger.info(f"   Calling catalog_service.list_tables_in_schema('{catalog_name}', '{schema_name}')...")
        tables = await catalog_service.list_tables_in_schema(catalog_name, schema_name, current_user.user_id)

        logger.info(f"   ✅ Retrieved {len(tables)} tables in {catalog_name}.{schema_name}:")
        for table in tables:
            logger.info(f"      - {table.name} (type: {table.table_type}, full: {table.full_name})")

        # Apply filters
        if search:
            search_lower = search.lower()
            original_count = len(tables)
            tables = [t for t in tables if search_lower in t.name.lower() or
                     (t.comment and search_lower in t.comment.lower())]
            logger.info(f"   🔍 Search filter '{search}' reduced from {original_count} to {len(tables)} tables")

        if table_type:
            original_count = len(tables)
            tables = [t for t in tables if t.table_type and t.table_type.lower() == table_type.lower()]
            logger.info(f"   🔍 Type filter '{table_type}' reduced from {original_count} to {len(tables)} tables")

        logger.info(f"   📤 Returning {len(tables)} tables to client")
        logger.info("="*80)
        return TablesResponse(tables=tables)
    except Exception as e:
        logger.error(f"❌ Error listing tables for {catalog_name}.{schema_name}: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tables in schema {catalog_name}.{schema_name}: {str(e)}"
        )


@router.get("/{catalog_name}/{schema_name}/{table_name}/columns", response_model=ColumnsResponse)
async def get_table_columns(
    catalog_name: str,
    schema_name: str,
    table_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get all columns for a table"""
    try:
        columns = await catalog_service.get_table_columns(
            catalog_name, schema_name, table_name, current_user.user_id
        )
        return ColumnsResponse(columns=columns)
    except Exception as e:
        logger.error(f"Error getting columns for {catalog_name}.{schema_name}.{table_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get columns for table {catalog_name}.{schema_name}.{table_name}"
        )


@router.get("/search")
async def search_entities(
    query: str = Query(..., min_length=2, description="Search query"),
    entity_types: List[str] = Query(["catalog", "schema", "table", "column"], description="Types to search"),
    current_user: User = Depends(get_current_active_user)
):
    """Search for entities across all catalogs"""
    try:
        results = await catalog_service.search_entities(query, entity_types, current_user.user_id)
        return {
            "query": query,
            "entity_types": entity_types,
            "results": results
        }
    except Exception as e:
        logger.error(f"Error searching entities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search entities"
        )