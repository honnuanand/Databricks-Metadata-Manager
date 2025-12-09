#!/usr/bin/env python3
import os
"""
Execute schema creation SQL in FEVM workspace
"""
from databricks.sdk import WorkspaceClient
import time

# FEVM configuration
client = WorkspaceClient(
    host="https://fe-vm-leaps-fe.cloud.databricks.com",
    token=os.environ["DATABRICKS_TOKEN"]
)

def execute_sql_statements(sql_file):
    """Execute SQL statements from file"""
    with open(sql_file, 'r') as f:
        sql_content = f.read()

    # Split by semicolon to get individual statements
    statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]

    print(f"Found {len(statements)} SQL statements to execute")

    # Use the patrick-warehouse in FEVM
    warehouse_id = "2dc6b7aacc451bcd"  # patrick-warehouse

    success_count = 0
    error_count = 0

    for i, statement in enumerate(statements, 1):
        # Skip comments and empty lines
        if not statement or statement.startswith('--'):
            continue

        print(f"\n[{i}/{len(statements)}] Executing:")
        print(f"{statement[:100]}..." if len(statement) > 100 else statement)

        try:
            # Execute the SQL statement
            result = client.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=statement,
                wait_timeout="30s"
            )

            if result.status.state == "SUCCEEDED":
                print(f"✅ Success")
                success_count += 1
            else:
                print(f"⚠️  Status: {result.status.state}")
                if result.status.error:
                    print(f"   Error: {result.status.error.message}")
                error_count += 1

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            error_count += 1
            # Continue with next statement

        # Small delay between statements
        time.sleep(0.5)

    print(f"\n{'='*80}")
    print(f"EXECUTION SUMMARY")
    print(f"{'='*80}")
    print(f"Total statements: {len(statements)}")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {error_count}")

    return success_count, error_count

if __name__ == "__main__":
    print("="*80)
    print("FEVM SCHEMA SETUP")
    print("="*80)
    print(f"Workspace: fe-vm-leaps-fe.cloud.databricks.com")
    print(f"Creating schemas: main.metadata_manager, main.metadata_test")
    print("="*80)

    success, errors = execute_sql_statements('create_schemas_fevm.sql')

    if errors == 0:
        print(f"\n🎉 All schemas and tables created successfully!")
    else:
        print(f"\n⚠️  Completed with {errors} errors. Review output above.")
