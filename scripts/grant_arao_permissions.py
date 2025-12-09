#!/usr/bin/env python3
import os
"""
Grant permissions on arao catalog to the Metadata Manager app
"""
from databricks.sdk import WorkspaceClient

# FEVM configuration
client = WorkspaceClient(
    host="https://fe-vm-leaps-fe.cloud.databricks.com",
    token=os.environ["DATABRICKS_TOKEN"]
)

def grant_permissions():
    """Grant permissions on arao catalog to metadata-manager app"""

    # Use the patrick-warehouse in FEVM
    warehouse_id = "2dc6b7aacc451bcd"

    # Try different service principal name formats
    service_principals = [
        "metadata-manager",
        "2409307273843806-metadata-manager",  # workspace-id format
        "`metadata-manager`",
    ]

    grant_statements = [
        "GRANT USE CATALOG ON CATALOG arao TO `{sp}`",
        "GRANT USE SCHEMA ON SCHEMA arao.metadata_manager TO `{sp}`",
        "GRANT USE SCHEMA ON SCHEMA arao.metadata_test TO `{sp}`",
        "GRANT SELECT ON SCHEMA arao.metadata_test TO `{sp}`",
        "GRANT ALL PRIVILEGES ON SCHEMA arao.metadata_manager TO `{sp}`",
    ]

    print("="*80)
    print("GRANTING PERMISSIONS ON ARAO CATALOG")
    print("="*80)

    for sp in service_principals:
        print(f"\n🔑 Trying service principal: {sp}")
        success_count = 0

        for statement_template in grant_statements:
            # Format the statement with service principal
            statement = statement_template.format(sp=sp.strip('`'))

            try:
                print(f"\n   Executing: {statement}")
                result = client.statement_execution.execute_statement(
                    warehouse_id=warehouse_id,
                    statement=statement,
                    wait_timeout="30s"
                )

                if result.status.state == "SUCCEEDED":
                    print(f"   ✅ Success")
                    success_count += 1
                else:
                    print(f"   ⚠️  Status: {result.status.state}")
                    if result.status.error:
                        print(f"   Error: {result.status.error.message}")

            except Exception as e:
                error_msg = str(e)
                if "does not exist" in error_msg.lower() or "cannot find" in error_msg.lower():
                    print(f"   ❌ Service principal not found")
                    break  # Try next SP format
                else:
                    print(f"   ⚠️  Error: {error_msg}")

        if success_count == len(grant_statements):
            print(f"\n✅ All permissions granted successfully for {sp}")
            return True

    print(f"\n❌ Could not grant permissions. Please check service principal name.")
    print(f"\nTo find the correct service principal name:")
    print(f"1. Add a debug endpoint to your app that returns: SELECT current_user()")
    print(f"2. Or check Databricks workspace -> Settings -> Identity & Access -> Service Principals")
    return False

if __name__ == "__main__":
    print("="*80)
    print("ARAO CATALOG PERMISSIONS SETUP")
    print("="*80)
    print(f"Workspace: fe-vm-leaps-fe.cloud.databricks.com")
    print(f"Catalog: arao")
    print(f"Schemas: metadata_manager, metadata_test")
    print("="*80)

    success = grant_permissions()

    if success:
        print(f"\n🎉 Permissions granted successfully!")
        print(f"\nThe metadata-manager app should now be able to:")
        print(f"  ✅ Browse the arao catalog")
        print(f"  ✅ List schemas: metadata_manager, metadata_test")
        print(f"  ✅ View tables in both schemas")
        print(f"  ✅ Read from metadata_test tables")
        print(f"  ✅ Read/write metadata_manager tables")
    else:
        print(f"\n⚠️  Manual steps required:")
        print(f"\n1. Find the app's service principal name:")
        print(f"   - In the app, check the /debug-config endpoint")
        print(f"   - Or run: SELECT current_user() from within the app")
        print(f"\n2. Run these grants manually in FEVM SQL warehouse:")
        print(f"   GRANT USE CATALOG ON CATALOG arao TO `<service-principal-name>`;")
        print(f"   GRANT USE SCHEMA ON SCHEMA arao.metadata_manager TO `<service-principal-name>`;")
        print(f"   GRANT USE SCHEMA ON SCHEMA arao.metadata_test TO `<service-principal-name>`;")
        print(f"   GRANT SELECT ON SCHEMA arao.metadata_test TO `<service-principal-name>`;")
        print(f"   GRANT ALL PRIVILEGES ON SCHEMA arao.metadata_manager TO `<service-principal-name>`;")
