"""
Pre-flight checks for Metadata Manager installer.

Validates all prerequisites before installation begins:
- Databricks CLI installation and configuration
- Python dependencies
- Node.js and npm
- Network connectivity
- User permissions
"""

import subprocess
import shutil
import json
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass


@dataclass
class CheckResult:
    """Result of a pre-flight check"""
    name: str
    passed: bool
    message: str
    details: Optional[str] = None


class PreflightChecker:
    """Runs all pre-flight checks before installation"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[CheckResult] = []

    def run_command(self, command: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
        """Run a shell command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                check=False,
                timeout=30
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except Exception as e:
            return 1, "", str(e)

    def check_databricks_cli(self) -> CheckResult:
        """Check if Databricks CLI is installed and configured"""
        # Check if databricks command exists
        if not shutil.which("databricks"):
            return CheckResult(
                name="Databricks CLI",
                passed=False,
                message="Databricks CLI not found",
                details="Install with: pip install databricks-cli"
            )

        # Check version
        exit_code, stdout, stderr = self.run_command(["databricks", "--version"])
        if exit_code != 0:
            return CheckResult(
                name="Databricks CLI",
                passed=False,
                message="Cannot get Databricks CLI version",
                details=stderr
            )

        version = stdout.strip()

        # Check if configured
        exit_code, stdout, stderr = self.run_command(["databricks", "auth", "env", "--profile", "DEFAULT"])
        if exit_code != 0:
            return CheckResult(
                name="Databricks CLI",
                passed=False,
                message="Databricks CLI not configured",
                details="Run: databricks configure --token"
            )

        return CheckResult(
            name="Databricks CLI",
            passed=True,
            message=f"Installed ({version})",
            details=None
        )

    def check_python_dependencies(self) -> CheckResult:
        """Check if required Python packages are installed"""
        required_packages = [
            "databricks-sdk",
            "pyyaml",
            "sqlalchemy",
            "alembic",
            "psycopg2-binary",
            "passlib",
            "bcrypt",
        ]

        missing = []
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing.append(package)

        if missing:
            return CheckResult(
                name="Python Dependencies",
                passed=False,
                message=f"Missing packages: {', '.join(missing)}",
                details=f"Install with: pip install {' '.join(missing)}"
            )

        return CheckResult(
            name="Python Dependencies",
            passed=True,
            message="All required packages installed"
        )

    def check_nodejs(self) -> CheckResult:
        """Check if Node.js and npm are installed"""
        if not shutil.which("node"):
            return CheckResult(
                name="Node.js",
                passed=False,
                message="Node.js not found",
                details="Install Node.js 18+ from https://nodejs.org"
            )

        exit_code, stdout, stderr = self.run_command(["node", "--version"])
        if exit_code != 0:
            return CheckResult(
                name="Node.js",
                passed=False,
                message="Cannot get Node.js version",
                details=stderr
            )

        version = stdout.strip()
        # Check minimum version (18.x)
        try:
            major_version = int(version.lstrip("v").split(".")[0])
            if major_version < 18:
                return CheckResult(
                    name="Node.js",
                    passed=False,
                    message=f"Node.js {version} is too old",
                    details="Requires Node.js 18 or higher"
                )
        except (ValueError, IndexError):
            pass

        # Check npm
        if not shutil.which("npm"):
            return CheckResult(
                name="Node.js",
                passed=False,
                message="npm not found",
                details="npm should be installed with Node.js"
            )

        return CheckResult(
            name="Node.js",
            passed=True,
            message=f"Installed ({version})"
        )

    def check_databricks_connectivity(self, host: str = None, token: str = None) -> CheckResult:
        """Check connectivity to Databricks workspace"""
        if not host or not token:
            # Try to get from CLI config
            exit_code, stdout, stderr = self.run_command(["databricks", "workspace", "list", "/"])
            if exit_code != 0:
                return CheckResult(
                    name="Databricks Connectivity",
                    passed=False,
                    message="Cannot connect to Databricks",
                    details="Check CLI configuration or provide host/token"
                )
            return CheckResult(
                name="Databricks Connectivity",
                passed=True,
                message="Connected via CLI configuration"
            )

        # Test with provided credentials
        exit_code, stdout, stderr = self.run_command([
            "databricks", "workspace", "list", "/",
            "--host", host, "--token", token
        ])

        if exit_code != 0:
            return CheckResult(
                name="Databricks Connectivity",
                passed=False,
                message="Cannot connect to Databricks workspace",
                details=stderr
            )

        return CheckResult(
            name="Databricks Connectivity",
            passed=True,
            message=f"Connected to {host}"
        )

    def check_postgres_connectivity(self, database_url: str = None) -> CheckResult:
        """Check connectivity to PostgreSQL database"""
        if not database_url:
            return CheckResult(
                name="PostgreSQL Connectivity",
                passed=False,
                message="Database URL not provided",
                details="Will be prompted during installation"
            )

        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(database_url, pool_pre_ping=True, pool_size=1)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            engine.dispose()

            return CheckResult(
                name="PostgreSQL Connectivity",
                passed=True,
                message="Connected successfully"
            )
        except Exception as e:
            return CheckResult(
                name="PostgreSQL Connectivity",
                passed=False,
                message="Cannot connect to PostgreSQL",
                details=str(e)
            )

    def check_warehouse_accessible(self, host: str = None, token: str = None, warehouse_id: str = None) -> CheckResult:
        """Check if SQL warehouse is accessible"""
        if not warehouse_id:
            return CheckResult(
                name="SQL Warehouse",
                passed=False,
                message="Warehouse ID not provided",
                details="Will be prompted during installation"
            )

        try:
            exit_code, stdout, stderr = self.run_command([
                "databricks", "warehouses", "get", warehouse_id, "--output", "json"
            ])

            if exit_code != 0:
                return CheckResult(
                    name="SQL Warehouse",
                    passed=False,
                    message=f"Cannot access warehouse {warehouse_id}",
                    details=stderr
                )

            warehouse_info = json.loads(stdout)
            state = warehouse_info.get("state", "UNKNOWN")

            if state == "RUNNING":
                return CheckResult(
                    name="SQL Warehouse",
                    passed=True,
                    message=f"Warehouse {warehouse_id} is running"
                )
            elif state == "STOPPED":
                return CheckResult(
                    name="SQL Warehouse",
                    passed=True,
                    message=f"Warehouse {warehouse_id} is stopped (will be started)",
                    details="Warehouse will be started automatically"
                )
            else:
                return CheckResult(
                    name="SQL Warehouse",
                    passed=False,
                    message=f"Warehouse state: {state}",
                    details="Warehouse must be in RUNNING or STOPPED state"
                )

        except json.JSONDecodeError:
            return CheckResult(
                name="SQL Warehouse",
                passed=False,
                message="Invalid response from warehouse API",
                details=stdout
            )
        except Exception as e:
            return CheckResult(
                name="SQL Warehouse",
                passed=False,
                message="Error checking warehouse",
                details=str(e)
            )

    def check_user_permissions(self) -> CheckResult:
        """Check if current user has required permissions"""
        try:
            exit_code, stdout, stderr = self.run_command([
                "databricks", "current-user", "me", "--output", "json"
            ])

            if exit_code != 0:
                return CheckResult(
                    name="User Permissions",
                    passed=False,
                    message="Cannot get current user info",
                    details=stderr
                )

            user_info = json.loads(stdout)
            user_name = user_info.get("userName", "Unknown")

            return CheckResult(
                name="User Permissions",
                passed=True,
                message=f"Authenticated as {user_name}"
            )

        except Exception as e:
            return CheckResult(
                name="User Permissions",
                passed=False,
                message="Error checking user permissions",
                details=str(e)
            )

    def run_all_checks(
        self,
        host: str = None,
        token: str = None,
        warehouse_id: str = None,
        database_url: str = None
    ) -> Tuple[bool, List[CheckResult]]:
        """Run all pre-flight checks"""
        self.results = []

        # Essential checks
        self.results.append(self.check_databricks_cli())
        self.results.append(self.check_python_dependencies())
        self.results.append(self.check_nodejs())
        self.results.append(self.check_user_permissions())

        # Connectivity checks (may pass with warnings if values not provided)
        self.results.append(self.check_databricks_connectivity(host, token))

        if warehouse_id:
            self.results.append(self.check_warehouse_accessible(host, token, warehouse_id))

        if database_url:
            self.results.append(self.check_postgres_connectivity(database_url))

        # Check if any essential checks failed
        essential_checks = ["Databricks CLI", "Python Dependencies", "Node.js"]
        all_passed = True
        for result in self.results:
            if result.name in essential_checks and not result.passed:
                all_passed = False
                break

        return all_passed, self.results

    def print_results(self) -> None:
        """Print pre-flight check results"""
        print("\nPre-flight Checks")
        print("=" * 50)

        for result in self.results:
            status = "[PASS]" if result.passed else "[FAIL]"
            print(f"{status} {result.name}: {result.message}")
            if result.details and (not result.passed or self.verbose):
                print(f"       {result.details}")

        print()

    def get_failures(self) -> List[CheckResult]:
        """Get list of failed checks"""
        return [r for r in self.results if not r.passed]
