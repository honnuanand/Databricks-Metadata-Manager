#!/usr/bin/env python3
"""
Grant permissions on arao catalog to the metadata-manager app service principal
"""
import os
from databricks.sdk import WorkspaceClient

# FEVM configuration - requires DATABRICKS_TOKEN environment variable
client = WorkspaceClient(
    host="https://fe-vm-leaps-fe.cloud.databricks.com",
    token=os.environ["DATABRICKS_TOKEN"]
)

def grant_arao_permissions():
    """Grant permissions on arao catalog"""

    warehouse_id = "2dc6b7aacc451bcd"  # patrick-warehouse
    service_principal = "app-1i54xz metadata-manager"

    grants = [
        f"GRANT USE CATALOG ON CATALOG arao TO `{service_principal}`",
        f"GRANT USE SCHEMA ON SCHEMA arao.metadata_manager TO `{service_principal}`",
        f"GRANT USE SCHEMA ON SCHEMA arao.metadata_test TO `{service_principal}`",
        f"GRANT SELECT ON SCHEMA arao.metadata_test TO `{service_principal}`",
        f"GRANT ALL PRIVILEGES ON SCHEMA arao.metadata_manager TO `{service_principal}`",
    ]

    print("="*80)
    print(f"GRANTING PERMISSIONS ON ARAO CATALOG")
    print(f"Service Principal: {service_principal}")
    print("="*80)

    for grant in grants:
        print(f"\n🔑 {grant}")
        try:
            result = client.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=grant,
                wait_timeout="30s"
            )

            if result.status.state == "SUCCEEDED":
                print(f"   ✅ Success")
            else:
                print(f"   ⚠️  Status: {result.status.state}")
                if result.status.error:
                    print(f"   Error: {result.status.error.message}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

    print(f"\n{'='*80}")
    print(f"✅ Permissions granted!")
    print(f"{'='*80}")
    print(f"\nThe metadata-manager app can now:")
    print(f"  ✅ Browse the arao catalog")
    print(f"  ✅ List schemas: metadata_manager, metadata_test")
    print(f"  ✅ View all tables")
    print(f"  ✅ Read from metadata_test")
    print(f"  ✅ Read/write to metadata_manager")
    print(f"\nClick the REFRESH button in Catalog Explorer to see arao!")

if __name__ == "__main__":
    grant_arao_permissions()
