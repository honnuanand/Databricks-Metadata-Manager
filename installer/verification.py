"""
Installation verification for Metadata Manager installer.

Verifies all components are correctly installed and generates a report.
"""

import subprocess
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VerificationItem:
    """Single verification check"""
    name: str
    passed: bool
    message: str
    details: Optional[str] = None


@dataclass
class InstallationReport:
    """Complete installation report"""
    timestamp: str = ""
    workspace_url: str = ""
    catalog: str = ""
    secret_scope: str = ""
    app_url: str = ""
    verifications: List[VerificationItem] = field(default_factory=list)
    seed_credentials: List[Dict] = field(default_factory=list)

    def all_passed(self) -> bool:
        return all(v.passed for v in self.verifications)


class InstallationVerifier:
    """Verifies installation completeness"""

    def __init__(
        self,
        workspace_url: str = "",
        catalog: str = "arao",
        schema_primary: str = "metadata_manager",
        schema_test: str = "metadata_test",
        secret_scope: str = "metadata-manager-secrets",
        database_url: str = "",
        app_name: str = "metadata-manager",
        warehouse_id: str = ""
    ):
        self.workspace_url = workspace_url
        self.catalog = catalog
        self.schema_primary = schema_primary
        self.schema_test = schema_test
        self.secret_scope = secret_scope
        self.database_url = database_url
        self.app_name = app_name
        self.warehouse_id = warehouse_id
        self.report = InstallationReport()

    def run_command(self, command: List[str]) -> tuple:
        """Run a shell command"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=60
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)

    def verify_secrets(self) -> VerificationItem:
        """Verify secret scope has all required secrets"""
        required_secrets = ["databricks-token", "databricks-host", "secret-key", "database-url"]

        exit_code, stdout, stderr = self.run_command([
            "databricks", "secrets", "list-secrets", self.secret_scope
        ])

        if exit_code != 0:
            return VerificationItem(
                name="Secret Scope",
                passed=False,
                message=f"Cannot access scope '{self.secret_scope}'",
                details=stderr
            )

        existing = []
        for line in stdout.strip().split('\n')[1:]:
            parts = line.split()
            if parts:
                existing.append(parts[0])

        missing = [s for s in required_secrets if s not in existing]

        if missing:
            return VerificationItem(
                name="Secret Scope",
                passed=False,
                message=f"Missing secrets: {', '.join(missing)}",
                details=f"Found: {', '.join(existing)}"
            )

        return VerificationItem(
            name="Secret Scope",
            passed=True,
            message=f"All {len(required_secrets)} secrets present"
        )

    def verify_databricks_schema(self, schema: str, expected_tables: List[str]) -> VerificationItem:
        """Verify a Databricks schema has all expected tables"""
        if not self.warehouse_id:
            return VerificationItem(
                name=f"Schema {self.catalog}.{schema}",
                passed=False,
                message="Warehouse ID not configured"
            )

        exit_code, stdout, stderr = self.run_command([
            "databricks", "sql", "execute",
            "--warehouse-id", self.warehouse_id,
            "--statement", f"SHOW TABLES IN {self.catalog}.{schema}",
            "--output", "json"
        ])

        if exit_code != 0:
            return VerificationItem(
                name=f"Schema {self.catalog}.{schema}",
                passed=False,
                message="Cannot list tables",
                details=stderr
            )

        try:
            result = json.loads(stdout) if stdout.strip() else {}
            tables = [row[1] for row in result.get("data_array", [])]
        except (json.JSONDecodeError, IndexError):
            tables = []

        missing = [t for t in expected_tables if t not in tables]

        if missing:
            return VerificationItem(
                name=f"Schema {self.catalog}.{schema}",
                passed=False,
                message=f"Missing tables: {', '.join(missing)}"
            )

        return VerificationItem(
            name=f"Schema {self.catalog}.{schema}",
            passed=True,
            message=f"All {len(expected_tables)} tables present"
        )

    def verify_postgres_tables(self) -> VerificationItem:
        """Verify PostgreSQL tables exist"""
        if not self.database_url:
            return VerificationItem(
                name="PostgreSQL Database",
                passed=False,
                message="Database URL not configured"
            )

        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.pool import NullPool

            engine = create_engine(self.database_url, poolclass=NullPool)
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                """))
                tables = [row[0] for row in result.fetchall()]
            engine.dispose()

            required = ["users", "alembic_version"]
            missing = [t for t in required if t not in tables]

            if missing:
                return VerificationItem(
                    name="PostgreSQL Database",
                    passed=False,
                    message=f"Missing tables: {', '.join(missing)}"
                )

            return VerificationItem(
                name="PostgreSQL Database",
                passed=True,
                message=f"{len(tables)} tables present"
            )

        except Exception as e:
            return VerificationItem(
                name="PostgreSQL Database",
                passed=False,
                message="Connection failed",
                details=str(e)
            )

    def verify_postgres_users(self) -> VerificationItem:
        """Verify seed users exist in PostgreSQL"""
        if not self.database_url:
            return VerificationItem(
                name="PostgreSQL Users",
                passed=False,
                message="Database URL not configured"
            )

        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.pool import NullPool

            engine = create_engine(self.database_url, poolclass=NullPool)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                count = result.scalar()
            engine.dispose()

            if count == 0:
                return VerificationItem(
                    name="PostgreSQL Users",
                    passed=False,
                    message="No users found"
                )

            return VerificationItem(
                name="PostgreSQL Users",
                passed=True,
                message=f"{count} users present"
            )

        except Exception as e:
            return VerificationItem(
                name="PostgreSQL Users",
                passed=False,
                message="Query failed",
                details=str(e)
            )

    def verify_app_deployed(self) -> VerificationItem:
        """Verify app is deployed and running"""
        exit_code, stdout, stderr = self.run_command([
            "databricks", "apps", "get", self.app_name, "--output", "json"
        ])

        if exit_code != 0:
            return VerificationItem(
                name="Databricks App",
                passed=False,
                message=f"App '{self.app_name}' not found"
            )

        try:
            app_info = json.loads(stdout)
            state = app_info.get("app_status", {}).get("state", "UNKNOWN")
            url = app_info.get("url", "")

            if state == "RUNNING":
                self.report.app_url = url
                return VerificationItem(
                    name="Databricks App",
                    passed=True,
                    message="Running",
                    details=url
                )
            else:
                return VerificationItem(
                    name="Databricks App",
                    passed=False,
                    message=f"State: {state}"
                )

        except json.JSONDecodeError:
            return VerificationItem(
                name="Databricks App",
                passed=False,
                message="Invalid app info response"
            )

    def run_all_verifications(self) -> InstallationReport:
        """Run all verification checks"""
        self.report = InstallationReport(
            timestamp=datetime.now().isoformat(),
            workspace_url=self.workspace_url,
            catalog=self.catalog,
            secret_scope=self.secret_scope
        )

        # Verify secrets
        self.report.verifications.append(self.verify_secrets())

        # Verify metadata_manager schema
        manager_tables = ["users", "comment_suggestions", "approvals", "audit_logs"]
        self.report.verifications.append(
            self.verify_databricks_schema(self.schema_primary, manager_tables)
        )

        # Verify metadata_test schema
        test_tables = ["users", "products", "orders", "order_items", "employees",
                       "customer_segments", "daily_sales_summary", "revenue_by_product"]
        self.report.verifications.append(
            self.verify_databricks_schema(self.schema_test, test_tables)
        )

        # Verify PostgreSQL
        self.report.verifications.append(self.verify_postgres_tables())
        self.report.verifications.append(self.verify_postgres_users())

        # Verify app
        self.report.verifications.append(self.verify_app_deployed())

        # Add seed credentials
        self.report.seed_credentials = [
            {"email": "admin@example.com", "password": "admin123", "role": "ADMIN"},
            {"email": "approver@example.com", "password": "approver123", "role": "APPROVER"},
            {"email": "user@example.com", "password": "user123", "role": "SUGGEST_ONLY"},
        ]

        return self.report

    def print_report(self) -> None:
        """Print the installation report"""
        print("\n" + "=" * 60)
        print("INSTALLATION REPORT")
        print("=" * 60)
        print(f"Timestamp: {self.report.timestamp}")
        print(f"Workspace: {self.report.workspace_url or 'N/A'}")
        print(f"Catalog: {self.report.catalog}")
        print(f"Secret Scope: {self.report.secret_scope}")
        print()

        print("Components:")
        print("-" * 40)
        for v in self.report.verifications:
            status = "[OK]" if v.passed else "[FAIL]"
            print(f"  {status} {v.name}: {v.message}")
            if v.details and not v.passed:
                print(f"       {v.details}")

        if self.report.app_url:
            print()
            print(f"App URL: {self.report.app_url}")

        print()
        print("Login Credentials:")
        print("-" * 40)
        for cred in self.report.seed_credentials:
            print(f"  {cred['role']:12} {cred['email']} / {cred['password']}")

        print()
        if self.report.all_passed():
            print("Installation completed successfully!")
        else:
            print("Installation has issues. Review failed checks above.")
        print("=" * 60)

    def generate_json_report(self) -> str:
        """Generate JSON report"""
        return json.dumps({
            "timestamp": self.report.timestamp,
            "workspace_url": self.report.workspace_url,
            "catalog": self.report.catalog,
            "secret_scope": self.report.secret_scope,
            "app_url": self.report.app_url,
            "verifications": [
                {
                    "name": v.name,
                    "passed": v.passed,
                    "message": v.message,
                    "details": v.details
                }
                for v in self.report.verifications
            ],
            "seed_credentials": self.report.seed_credentials,
            "all_passed": self.report.all_passed()
        }, indent=2)
