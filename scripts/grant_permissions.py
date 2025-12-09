#!/usr/bin/env python3
"""
Grant permissions to the Metadata Manager service principal.

This script should be run AFTER the app is deployed to grant the necessary
Unity Catalog permissions. The service principal name can be discovered by:
1. Checking the app logs
2. Adding a debug endpoint that returns current_user()
3. Using the --discover flag (requires app to be running)

Usage:
    # Interactive mode - prompts for service principal name
    python scripts/grant_permissions.py

    # Specify service principal directly
    python scripts/grant_permissions.py --principal "metadata-manager"

    # Use custom catalog/scope
    python scripts/grant_permissions.py --principal "metadata-manager" --catalog my_catalog

    # Dry run - show grants without executing
    python scripts/grant_permissions.py --principal "metadata-manager" --dry-run
"""

import argparse
import subprocess
import sys
import json
from typing import List, Tuple


def run_command(command: List[str]) -> Tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr"""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=60
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def get_warehouse_id() -> str:
    """Get the first available SQL warehouse ID"""
    exit_code, stdout, stderr = run_command([
        "databricks", "warehouses", "list", "--output", "json"
    ])

    if exit_code != 0:
        print(f"Error listing warehouses: {stderr}")
        return ""

    try:
        warehouses = json.loads(stdout)
        if warehouses:
            # Prefer running warehouses
            for wh in warehouses:
                if wh.get("state") == "RUNNING":
                    return wh.get("id", "")
            # Fall back to first warehouse
            return warehouses[0].get("id", "")
    except json.JSONDecodeError:
        pass

    return ""


def execute_sql(warehouse_id: str, statement: str) -> Tuple[bool, str]:
    """Execute a SQL statement via Databricks CLI"""
    exit_code, stdout, stderr = run_command([
        "databricks", "sql", "execute",
        "--warehouse-id", warehouse_id,
        "--statement", statement
    ])

    if exit_code != 0:
        return False, stderr
    return True, "OK"


def grant_permissions(
    warehouse_id: str,
    catalog: str,
    schema_primary: str,
    schema_test: str,
    service_principal: str,
    include_test_schema: bool = True,
    dry_run: bool = False
) -> Tuple[bool, List[str]]:
    """
    Grant all required permissions to the service principal.

    Returns:
        Tuple of (all_success, list of messages)
    """
    messages = []
    all_success = True

    grants = [
        (f"GRANT USE CATALOG ON CATALOG {catalog} TO `{service_principal}`",
         "USE CATALOG"),
        (f"GRANT USE SCHEMA ON SCHEMA {catalog}.{schema_primary} TO `{service_principal}`",
         f"USE SCHEMA on {schema_primary}"),
        (f"GRANT ALL PRIVILEGES ON SCHEMA {catalog}.{schema_primary} TO `{service_principal}`",
         f"ALL PRIVILEGES on {schema_primary}"),
    ]

    if include_test_schema:
        grants.extend([
            (f"GRANT USE SCHEMA ON SCHEMA {catalog}.{schema_test} TO `{service_principal}`",
             f"USE SCHEMA on {schema_test}"),
            (f"GRANT SELECT ON SCHEMA {catalog}.{schema_test} TO `{service_principal}`",
             f"SELECT on {schema_test}"),
        ])

    for sql, description in grants:
        if dry_run:
            messages.append(f"[DRY RUN] Would execute: {sql}")
        else:
            success, msg = execute_sql(warehouse_id, sql)
            if success:
                messages.append(f"[OK] Granted {description}")
            else:
                messages.append(f"[FAIL] {description}: {msg}")
                all_success = False

    return all_success, messages


def discover_service_principal(app_url: str) -> str:
    """
    Try to discover the service principal name from a running app.
    Requires the app to have a /api/v1/debug/current-user endpoint.
    """
    import urllib.request
    import urllib.error

    try:
        url = f"{app_url.rstrip('/')}/api/v1/debug/current-user"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get("current_user", "")
    except Exception as e:
        print(f"Could not discover service principal: {e}")
        return ""


def main():
    parser = argparse.ArgumentParser(
        description="Grant Unity Catalog permissions to Metadata Manager service principal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Interactive mode
    python scripts/grant_permissions.py

    # Specify principal directly
    python scripts/grant_permissions.py --principal "metadata-manager"

    # Custom catalog
    python scripts/grant_permissions.py --principal "app-xyz metadata-manager" --catalog my_catalog

    # Dry run
    python scripts/grant_permissions.py --principal "metadata-manager" --dry-run

Finding the service principal name:
    After deploying the app, the service principal name can be found by:
    1. Checking Databricks Apps logs for authentication info
    2. Adding a debug endpoint: @app.get("/debug/user") -> {"user": current_user()}
    3. Looking in Unity Catalog > Permissions for recent grants
        """
    )

    parser.add_argument("--principal", "-p", help="Service principal name (e.g., 'metadata-manager')")
    parser.add_argument("--catalog", "-c", default="arao", help="Catalog name (default: arao)")
    parser.add_argument("--schema", "-s", default="metadata_manager", help="Primary schema name (default: metadata_manager)")
    parser.add_argument("--test-schema", default="metadata_test", help="Test schema name (default: metadata_test)")
    parser.add_argument("--warehouse-id", "-w", help="SQL Warehouse ID (auto-detected if not provided)")
    parser.add_argument("--no-test-schema", action="store_true", help="Skip grants for test schema")
    parser.add_argument("--dry-run", action="store_true", help="Show grants without executing")
    parser.add_argument("--app-url", help="App URL to discover service principal (optional)")

    args = parser.parse_args()

    print("=" * 60)
    print("Metadata Manager Permission Grants")
    print("=" * 60)

    # Get warehouse ID
    warehouse_id = args.warehouse_id
    if not warehouse_id:
        print("\nDetecting SQL warehouse...")
        warehouse_id = get_warehouse_id()
        if not warehouse_id:
            print("Error: Could not find a SQL warehouse. Specify with --warehouse-id")
            return 1
        print(f"Using warehouse: {warehouse_id}")

    # Get service principal name
    principal = args.principal

    if not principal and args.app_url:
        print(f"\nTrying to discover service principal from {args.app_url}...")
        principal = discover_service_principal(args.app_url)
        if principal:
            print(f"Discovered: {principal}")

    if not principal:
        print("\nService principal name is required.")
        print("This is the identity the app runs as in Databricks.")
        print("Common formats:")
        print("  - metadata-manager")
        print("  - app-xxxxxx metadata-manager")
        print("  - <workspace-id>-metadata-manager")
        print()
        principal = input("Enter service principal name: ").strip()

        if not principal:
            print("Error: Service principal name is required")
            return 1

    # Confirm
    print(f"\nConfiguration:")
    print(f"  Catalog: {args.catalog}")
    print(f"  Schema: {args.schema}")
    print(f"  Test Schema: {args.test_schema}")
    print(f"  Service Principal: {principal}")
    print(f"  Include Test Schema: {not args.no_test_schema}")

    if not args.dry_run:
        confirm = input("\nProceed with granting permissions? [y/N]: ").strip().lower()
        if confirm != 'y':
            print("Cancelled.")
            return 0

    # Execute grants
    print("\nGranting permissions...")
    success, messages = grant_permissions(
        warehouse_id=warehouse_id,
        catalog=args.catalog,
        schema_primary=args.schema,
        schema_test=args.test_schema,
        service_principal=principal,
        include_test_schema=not args.no_test_schema,
        dry_run=args.dry_run
    )

    for msg in messages:
        print(f"  {msg}")

    if success:
        print("\nAll permissions granted successfully!")
        print(f"\nThe app '{principal}' now has access to:")
        print(f"  - {args.catalog}.{args.schema} (read/write)")
        if not args.no_test_schema:
            print(f"  - {args.catalog}.{args.test_schema} (read-only)")
    else:
        print("\nSome permissions failed. Check the errors above.")
        print("\nCommon issues:")
        print("  - Service principal name is incorrect")
        print("  - You don't have permission to grant on this catalog")
        print("  - The catalog/schema doesn't exist")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
