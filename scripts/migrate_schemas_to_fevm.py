#!/usr/bin/env python3
import os
"""
Migrate schemas and tables from E2Demo (arao catalog) to FEVM workspace
"""
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import SchemaInfo, TableInfo
import json

# E2Demo configuration
e2_client = WorkspaceClient(
    host="https://e2-demo-field-eng.cloud.databricks.com",
    token=os.environ["DATABRICKS_TOKEN"]
)

# FEVM configuration
fevm_client = WorkspaceClient(
    host="https://fe-vm-leaps-fe.cloud.databricks.com",
    token=os.environ["DATABRICKS_TOKEN"]
)

def get_schema_info(client, catalog_name, schema_name):
    """Get schema details"""
    try:
        schemas = list(client.schemas.list(catalog_name=catalog_name))
        for schema in schemas:
            if schema.name == schema_name:
                return schema
        return None
    except Exception as e:
        print(f"Error getting schema {catalog_name}.{schema_name}: {e}")
        return None

def get_tables_in_schema(client, catalog_name, schema_name):
    """Get all tables in a schema"""
    try:
        tables = list(client.tables.list(
            catalog_name=catalog_name,
            schema_name=schema_name
        ))
        return tables
    except Exception as e:
        print(f"Error getting tables in {catalog_name}.{schema_name}: {e}")
        return []

def get_table_ddl(client, full_table_name):
    """Get table DDL using SQL"""
    try:
        # This would need SQL connection - let's use describe instead
        table = client.tables.get(full_name=full_table_name)
        return table
    except Exception as e:
        print(f"Error getting table {full_table_name}: {e}")
        return None

def main():
    print("=" * 80)
    print("SCHEMA MIGRATION: E2Demo -> FEVM")
    print("=" * 80)

    source_catalog = "arao"
    target_catalog = "main"  # FEVM typically uses 'main' catalog
    schemas_to_migrate = ["metadata_manager", "metadata_test"]

    print(f"\n📋 Analyzing source schemas in E2Demo...")
    print(f"Source: {source_catalog} catalog")
    print(f"Schemas: {', '.join(schemas_to_migrate)}")

    for schema_name in schemas_to_migrate:
        print(f"\n{'='*60}")
        print(f"Processing: {source_catalog}.{schema_name}")
        print(f"{'='*60}")

        # Get schema info from E2Demo
        schema_info = get_schema_info(e2_client, source_catalog, schema_name)
        if schema_info:
            print(f"✅ Found schema: {schema_info.name}")
            print(f"   Owner: {schema_info.owner}")
            print(f"   Comment: {schema_info.comment or '(no comment)'}")
        else:
            print(f"❌ Schema not found: {source_catalog}.{schema_name}")
            continue

        # Get tables in schema
        tables = get_tables_in_schema(e2_client, source_catalog, schema_name)
        print(f"\n📊 Found {len(tables)} tables:")

        for table in tables:
            print(f"\n  Table: {table.name}")
            print(f"  Type: {table.table_type}")
            print(f"  Owner: {table.owner}")
            print(f"  Full name: {table.full_name}")

            # Get detailed table info
            table_detail = get_table_ddl(e2_client, table.full_name)
            if table_detail and table_detail.columns:
                print(f"  Columns ({len(table_detail.columns)}):")
                for col in table_detail.columns:
                    nullable = "NULL" if col.nullable else "NOT NULL"
                    print(f"    - {col.name}: {col.type_text or col.type_name} {nullable}")
                    if col.comment:
                        print(f"      Comment: {col.comment}")

    print(f"\n{'='*80}")
    print("MIGRATION PLAN")
    print(f"{'='*80}")
    print(f"\nTo migrate these schemas to FEVM, run the following SQL commands:")
    print(f"(You can execute these in a FEVM SQL warehouse)")

    for schema_name in schemas_to_migrate:
        print(f"\n-- Create schema {schema_name} in FEVM")
        print(f"CREATE SCHEMA IF NOT EXISTS {target_catalog}.{schema_name};")

        tables = get_tables_in_schema(e2_client, source_catalog, schema_name)
        for table in tables:
            table_detail = get_table_ddl(e2_client, table.full_name)
            if table_detail and table_detail.columns:
                print(f"\n-- Create table {table.name}")
                columns_def = []
                for col in table_detail.columns:
                    nullable = "" if col.nullable else " NOT NULL"
                    comment = f" COMMENT '{col.comment}'" if col.comment else ""
                    columns_def.append(f"  {col.name} {col.type_text or col.type_name}{nullable}{comment}")

                columns_str = ",\n".join(columns_def)
                table_comment = f"\nCOMMENT '{table_detail.comment}'" if table_detail.comment else ""

                print(f"CREATE TABLE IF NOT EXISTS {target_catalog}.{schema_name}.{table.name} (")
                print(columns_str)
                print(f"){table_comment};")

if __name__ == "__main__":
    main()
