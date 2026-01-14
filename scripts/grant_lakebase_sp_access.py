#!/usr/bin/env python3
"""
Grant Lakebase (PostgreSQL) access to a Databricks App Service Principal.

For Lakebase, you need to:
1. Create a PostgreSQL role with the SP's client_id as the role name
2. Set a security label for OAuth authentication
3. Grant schema permissions

Usage:
    python scripts/grant_lakebase_sp_access.py --profile fe-vm-leaps-fe --schema metadata_manager
"""

import argparse
import json
import subprocess
import sys
import os
import uuid

def get_app_sp_info(app_name: str, profile: str) -> dict:
    """Get Service Principal info from Databricks App"""
    result = subprocess.run(
        ["databricks", "apps", "get", app_name, "--profile", profile, "--output", "json"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"Error getting app info: {result.stderr}")
        return None

    app_info = json.loads(result.stdout)

    return {
        "client_id": app_info.get("service_principal_client_id"),
        "sp_id": app_info.get("service_principal_id"),
        "sp_name": app_info.get("service_principal_name"),
    }


def grant_lakebase_access(
    profile: str,
    sp_client_id: str,
    sp_id: int,
    schema_name: str,
    lakebase_instance: str,
    lakebase_host: str,
    dry_run: bool = False
):
    """Grant Lakebase access to the Service Principal"""
    from databricks.sdk import WorkspaceClient
    import psycopg

    print(f"\nConnecting to Lakebase...")
    print(f"  Instance: {lakebase_instance}")
    print(f"  Host: {lakebase_host}")

    # Create workspace client
    w = WorkspaceClient(profile=profile)
    me = w.current_user.me()
    print(f"  User: {me.user_name}")

    # Generate OAuth token
    cred = w.database.generate_database_credential(
        request_id=str(uuid.uuid4()),
        instance_names=[lakebase_instance]
    )

    # Connect to Lakebase
    conn = psycopg.connect(
        host=lakebase_host,
        port=5432,
        dbname='databricks_postgres',
        user=me.user_name,
        password=cred.token,
        sslmode='require',
        autocommit=True
    )

    print("  Connected!")

    with conn.cursor() as cur:
        # 1. Create PostgreSQL role with SP client ID as name
        print(f"\n1. Creating PostgreSQL role for SP...")
        print(f"   Role name: {sp_client_id}")

        if dry_run:
            print(f"   [DRY RUN] Would create role")
        else:
            try:
                cur.execute(f'CREATE ROLE "{sp_client_id}" WITH LOGIN NOINHERIT')
                print(f"   Created role!")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"   Role already exists")
                else:
                    print(f"   Warning: {e}")

        # 2. Set security label for OAuth authentication
        print(f"\n2. Setting security label for OAuth...")
        label = f"id={sp_id},type=SERVICE_PRINCIPAL"
        print(f"   Label: {label}")

        if dry_run:
            print(f"   [DRY RUN] Would set security label")
        else:
            try:
                cur.execute(f'''
                    SECURITY LABEL FOR databricks_auth ON ROLE "{sp_client_id}" IS '{label}'
                ''')
                print(f"   Security label set!")
            except Exception as e:
                print(f"   Warning: {e}")

        # 3. Grant schema permissions
        print(f"\n3. Granting schema permissions...")
        print(f"   Schema: {schema_name}")

        grants = [
            f'GRANT USAGE ON SCHEMA {schema_name} TO "{sp_client_id}"',
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {schema_name} TO "{sp_client_id}"',
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{sp_client_id}"',
            f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {schema_name} TO "{sp_client_id}"',
            f'ALTER DEFAULT PRIVILEGES IN SCHEMA {schema_name} GRANT USAGE, SELECT ON SEQUENCES TO "{sp_client_id}"',
        ]

        for grant in grants:
            if dry_run:
                print(f"   [DRY RUN] {grant}")
            else:
                try:
                    cur.execute(grant)
                    print(f"   OK: {grant[:60]}...")
                except Exception as e:
                    print(f"   Warning: {e}")

    conn.close()
    print("\nLakebase access granted!")


def main():
    parser = argparse.ArgumentParser(description="Grant Lakebase access to Databricks App SP")
    parser.add_argument("--profile", required=True, help="Databricks CLI profile")
    parser.add_argument("--app-name", default="metadata-manager", help="Databricks App name")
    parser.add_argument("--schema", default="metadata_manager", help="Lakebase schema name")
    parser.add_argument("--lakebase-instance", default="arao-lb", help="Lakebase instance name")
    parser.add_argument("--lakebase-host",
        default="instance-f2a8b56a-7fe2-4c9c-a0a3-7768594a50e5.database.cloud.databricks.com",
        help="Lakebase hostname")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")

    args = parser.parse_args()

    print("=" * 60)
    print("Grant Lakebase Access to Service Principal")
    print("=" * 60)

    # Get SP info
    print(f"\nGetting SP info for app: {args.app_name}")
    sp_info = get_app_sp_info(args.app_name, args.profile)

    if not sp_info or not sp_info.get("client_id"):
        print("Could not get Service Principal info")
        sys.exit(1)

    print(f"  Client ID: {sp_info['client_id']}")
    print(f"  SP ID: {sp_info['sp_id']}")
    print(f"  SP Name: {sp_info['sp_name']}")

    # Grant access
    grant_lakebase_access(
        profile=args.profile,
        sp_client_id=sp_info['client_id'],
        sp_id=sp_info['sp_id'],
        schema_name=args.schema,
        lakebase_instance=args.lakebase_instance,
        lakebase_host=args.lakebase_host,
        dry_run=args.dry_run
    )

    print("\n" + "=" * 60)
    print("Next steps:")
    print("  1. Redeploy the app to pick up new permissions")
    print("     python deploy_to_databricks.py --skip-secrets")
    print("=" * 60)


if __name__ == "__main__":
    main()
