#!/usr/bin/env python3
"""
Unified Installer for Databricks Metadata Manager

This script handles complete platform installation on a new Databricks workspace:
1. Pre-flight validation
2. Interactive credential collection
3. Secret scope creation and management
4. Databricks Unity Catalog schema/table setup
5. Neon PostgreSQL database setup
6. Permission grants
7. Frontend build and deployment

Usage:
    python install.py                          # Full interactive install
    python install.py --config config.yaml     # Use config file
    python install.py --dry-run                # Validate without executing
    python install.py --only secrets,schemas   # Run specific steps only
    python install.py --skip deploy            # Skip specific steps
    python install.py --init-config            # Generate config template
"""

import argparse
import getpass
import sys
from pathlib import Path

# Add installer package to path
sys.path.insert(0, str(Path(__file__).parent))

from installer.config import ConfigLoader, InstallConfig, generate_example_config
from installer.validators import (
    validate_databricks_host,
    validate_databricks_token,
    validate_postgres_url,
    validate_warehouse_id,
    validate_scope_name,
)
from installer.preflight import PreflightChecker
from installer.secrets_manager import SecretsManager
from installer.databricks_schema import DatabricksSchemaManager
from installer.postgres_setup import PostgresSetup
from installer.deployment import AppDeployer
from installer.verification import InstallationVerifier


class MetadataManagerInstaller:
    """Main installer orchestrator"""

    STEPS = [
        "preflight",
        "prompts",
        "secrets",
        "schemas",
        "permissions",
        "postgres",
        "frontend",
        "deploy",
        "verify",
    ]

    def __init__(self, config: InstallConfig, verbose: bool = False, dry_run: bool = False):
        self.config = config
        self.verbose = verbose
        self.dry_run = dry_run
        self.steps_completed = []

    def print_header(self, text: str):
        """Print a section header"""
        print()
        print("=" * 60)
        print(f"  {text}")
        print("=" * 60)

    def print_step(self, step_num: int, total: int, text: str):
        """Print a step header"""
        print()
        print(f"[Step {step_num}/{total}] {text}")
        print("-" * 40)

    def prompt_value(self, prompt: str, validator=None, secret: bool = False, default: str = None) -> str:
        """Prompt user for a value with optional validation"""
        while True:
            if default:
                display_prompt = f"{prompt} [{default}]: "
            else:
                display_prompt = f"{prompt}: "

            if secret:
                value = getpass.getpass(display_prompt)
            else:
                value = input(display_prompt).strip()

            if not value and default:
                value = default

            if not value:
                print("  Value is required. Please try again.")
                continue

            if validator:
                is_valid, error = validator(value)
                if not is_valid:
                    print(f"  Invalid: {error}")
                    continue

            return value

    def prompt_confirm(self, prompt: str, default: bool = True) -> bool:
        """Prompt for yes/no confirmation"""
        suffix = "[Y/n]" if default else "[y/N]"
        response = input(f"{prompt} {suffix}: ").strip().lower()

        if not response:
            return default

        return response in ("y", "yes")

    def run_preflight(self) -> bool:
        """Run pre-flight checks"""
        self.print_step(1, 9, "Pre-flight Checks")

        checker = PreflightChecker(verbose=self.verbose)
        all_passed, results = checker.run_all_checks(
            host=self.config.databricks.host,
            token=self.config.databricks.token,
            warehouse_id=self.config.databricks.warehouse_id,
            database_url=self.config.database.url
        )

        checker.print_results()

        if not all_passed:
            failures = checker.get_failures()
            essential_failures = [f for f in failures if f.name in ["Databricks CLI", "Python Dependencies", "Node.js"]]

            if essential_failures:
                print("Essential pre-flight checks failed. Please fix the issues above.")
                return False

        return True

    def run_prompts(self) -> bool:
        """Prompt for missing configuration values"""
        self.print_step(2, 9, "Configuration")

        missing = []

        # Check Databricks host
        if not self.config.databricks.host:
            print("\nDatabricks workspace URL is required.")
            print("Example: https://your-workspace.cloud.databricks.com")
            self.config.databricks.host = self.prompt_value(
                "Databricks host URL",
                validator=validate_databricks_host
            )
            missing.append("databricks_host")

        # Check Databricks token
        if not self.config.databricks.token:
            print("\nDatabricks Personal Access Token (PAT) is required.")
            print("Create one in Databricks: User Settings > Developer > Access Tokens")
            self.config.databricks.token = self.prompt_value(
                "Databricks PAT token",
                validator=validate_databricks_token,
                secret=True
            )
            missing.append("databricks_token")

        # Check warehouse ID
        if not self.config.databricks.warehouse_id:
            print("\nSQL Warehouse ID is required for running DDL statements.")
            print("Find it in: Databricks > SQL > SQL Warehouses > [warehouse] > Connection Details")
            self.config.databricks.warehouse_id = self.prompt_value(
                "SQL Warehouse ID",
                validator=validate_warehouse_id
            )
            missing.append("warehouse_id")

        # Check database URL
        if not self.config.database.url:
            print("\nNeon PostgreSQL connection URL is required.")
            print("Format: postgresql://user:password@host/database?sslmode=require")
            self.config.database.url = self.prompt_value(
                "Database URL",
                validator=validate_postgres_url,
                secret=True
            )
            missing.append("database_url")

        # Confirm configuration
        print("\nConfiguration Summary:")
        print(f"  Databricks Host: {self.config.databricks.host}")
        print(f"  Warehouse ID: {self.config.databricks.warehouse_id}")
        print(f"  Catalog: {self.config.catalog.name}")
        print(f"  Secret Scope: {self.config.secrets.scope_name}")
        print(f"  App Name: {self.config.deployment.app_name}")
        print(f"  Database URL: {self.config.database.url[:30]}...")

        if not self.prompt_confirm("\nProceed with installation?"):
            print("Installation cancelled.")
            return False

        return True

    def run_secrets(self) -> bool:
        """Set up secret scope and secrets"""
        self.print_step(3, 9, "Secret Scope Setup")

        manager = SecretsManager(verbose=self.verbose)

        # Generate secret key
        secret_key = manager.generate_secret_key()
        print(f"Generated JWT secret key: {secret_key[:16]}...")

        # Store for later use
        self.config.secrets.secret_key = secret_key
        self.config.secrets.databricks_token = self.config.databricks.token
        self.config.secrets.databricks_host = self.config.databricks.host
        self.config.secrets.database_url = self.config.database.url

        success, messages = manager.setup_secrets(
            scope_name=self.config.secrets.scope_name,
            databricks_token=self.config.databricks.token,
            databricks_host=self.config.databricks.host,
            database_url=self.config.database.url,
            secret_key=secret_key,
            dry_run=self.dry_run
        )

        for msg in messages:
            print(f"  {msg}")

        if not success:
            print("\nFailed to set up secrets.")
            return False

        print("\nSecrets configured successfully.")
        return True

    def run_schemas(self) -> bool:
        """Create Databricks schemas and tables"""
        self.print_step(4, 9, "Databricks Schema Setup")

        manager = DatabricksSchemaManager(
            warehouse_id=self.config.databricks.warehouse_id,
            verbose=self.verbose
        )

        success, messages = manager.setup_all_schemas(
            catalog=self.config.catalog.name,
            schema_primary=self.config.catalog.schema_primary,
            schema_test=self.config.catalog.schema_test,
            create_test_schema=self.config.catalog.create_test_schema,
            skip_existing=self.config.options.skip_existing,
            dry_run=self.dry_run
        )

        for msg in messages:
            print(f"  {msg}")

        if not success:
            print("\nFailed to create schemas.")
            return False

        print("\nDatabricks schemas created successfully.")
        return True

    def run_permissions(self) -> bool:
        """Grant permissions to service principal"""
        self.print_step(5, 9, "Permission Grants")

        if self.dry_run:
            print(f"  [DRY RUN] Would grant permissions to {self.config.service_principal.name}")
            return True

        manager = DatabricksSchemaManager(
            warehouse_id=self.config.databricks.warehouse_id,
            verbose=self.verbose
        )

        results = manager.grant_permissions(
            catalog=self.config.catalog.name,
            schema_primary=self.config.catalog.schema_primary,
            schema_test=self.config.catalog.schema_test,
            service_principal=self.config.service_principal.name
        )

        all_success = True
        for result in results:
            status = "[OK]" if result.success else "[FAIL]"
            print(f"  {status} {result.message}")
            if not result.success:
                all_success = False

        if not all_success:
            print("\nSome permission grants failed.")
            print("Note: This may be expected if service principal doesn't exist yet.")
            print("After first deployment, run SELECT current_user() to find the actual principal name.")

        return True  # Don't fail on permission errors

    def run_postgres(self) -> bool:
        """Set up PostgreSQL database"""
        self.print_step(6, 9, "PostgreSQL Setup")

        setup = PostgresSetup(
            database_url=self.config.database.url,
            backend_path=str(Path(__file__).parent / "backend"),
            verbose=self.verbose
        )

        success, messages = setup.setup_database(
            run_migrations=self.config.database.run_migrations,
            seed_data=self.config.database.seed_data,
            dry_run=self.dry_run
        )

        for msg in messages:
            print(f"  {msg}")

        setup.dispose()

        if not success:
            print("\nPostgreSQL setup failed.")
            return False

        print("\nPostgreSQL setup completed.")
        return True

    def run_frontend(self) -> bool:
        """Build frontend"""
        self.print_step(7, 9, "Frontend Build")

        if self.dry_run:
            print("  [DRY RUN] Would build frontend")
            return True

        deployer = AppDeployer(
            app_name=self.config.deployment.app_name,
            secret_scope=self.config.secrets.scope_name,
            verbose=self.verbose
        )

        success, msg = deployer.build_frontend()
        print(f"  {msg}")

        if not success:
            return False

        success, msg = deployer.copy_static_files()
        print(f"  {msg}")

        return success

    def run_deploy(self) -> bool:
        """Deploy to Databricks Apps"""
        self.print_step(8, 9, "Databricks Apps Deployment")

        deployer = AppDeployer(
            app_name=self.config.deployment.app_name,
            secret_scope=self.config.secrets.scope_name,
            workspace_path=self.config.deployment.workspace_path or None,
            verbose=self.verbose
        )

        # Get secrets for deployment
        database_url = self.config.secrets.database_url or self.config.database.url
        secret_key = self.config.secrets.secret_key

        if self.dry_run:
            print("  [DRY RUN] Would package backend")
            print("  [DRY RUN] Would upload to workspace")
            print("  [DRY RUN] Would deploy app")
            return True

        # Package backend
        success, msg = deployer.package_backend(database_url, secret_key)
        print(f"  {msg}")
        if not success:
            return False

        # Upload to workspace
        success, msg = deployer.upload_to_workspace()
        print(f"  {msg}")
        if not success:
            return False

        # Create/update app
        success, msg = deployer.create_app()
        print(f"  {msg}")
        if not success:
            return False

        # Deploy
        success, msg = deployer.deploy_app()
        print(f"  {msg}")
        if not success:
            return False

        # Wait for deployment
        print("  Waiting for app to start...")
        result = deployer.wait_for_deployment(timeout=300)
        print(f"  {result.message}")

        if result.app_url:
            print(f"\n  App URL: {result.app_url}")
            self.config.deployment.workspace_path = deployer.workspace_path

        # Cleanup
        deployer.cleanup()

        # Print post-deployment instructions for service principal permissions
        if result.success:
            print("\n" + "-" * 40)
            print("IMPORTANT: Post-Deployment Step Required")
            print("-" * 40)
            print("The app is now deployed but needs Unity Catalog permissions.")
            print("\n1. Find the service principal name by either:")
            print("   - Checking the app logs in Databricks")
            print("   - Visiting the app and checking /api/v1/debug/current-user")
            print("\n2. Run the permission grant script:")
            print(f"   python scripts/grant_permissions.py --principal \"<service-principal-name>\" --catalog {self.config.catalog.name}")
            print("\n   Or run interactively:")
            print("   python scripts/grant_permissions.py")

        return result.success

    def run_verify(self) -> bool:
        """Verify installation"""
        self.print_step(9, 9, "Verification")

        if self.dry_run:
            print("  [DRY RUN] Would verify installation")
            return True

        verifier = InstallationVerifier(
            workspace_url=self.config.databricks.host,
            catalog=self.config.catalog.name,
            schema_primary=self.config.catalog.schema_primary,
            schema_test=self.config.catalog.schema_test,
            secret_scope=self.config.secrets.scope_name,
            database_url=self.config.database.url,
            app_name=self.config.deployment.app_name,
            warehouse_id=self.config.databricks.warehouse_id
        )

        report = verifier.run_all_verifications()
        verifier.print_report()

        return report.all_passed()

    def run(self, only: list = None, skip: list = None) -> bool:
        """Run the installation"""
        self.print_header("Databricks Metadata Manager Installer")

        if self.dry_run:
            print("\n*** DRY RUN MODE - No changes will be made ***\n")

        steps_to_run = self.STEPS.copy()

        if only:
            steps_to_run = [s for s in steps_to_run if s in only]

        if skip:
            steps_to_run = [s for s in steps_to_run if s not in skip]

        step_methods = {
            "preflight": self.run_preflight,
            "prompts": self.run_prompts,
            "secrets": self.run_secrets,
            "schemas": self.run_schemas,
            "permissions": self.run_permissions,
            "postgres": self.run_postgres,
            "frontend": self.run_frontend,
            "deploy": self.run_deploy,
            "verify": self.run_verify,
        }

        for step in steps_to_run:
            if step in step_methods:
                success = step_methods[step]()
                if not success:
                    print(f"\nInstallation failed at step: {step}")
                    return False
                self.steps_completed.append(step)

        self.print_header("Installation Complete")
        print("\nAll steps completed successfully!")

        # Print final reminder about service principal permissions
        print("\nNext Steps:")
        print("1. Access the app and verify it loads correctly")
        print("2. Find the service principal name (check app logs or /api/v1/debug/current-user)")
        print("3. Grant permissions to the service principal:")
        print("   python scripts/grant_permissions.py --principal \"<name>\"")
        print("\nLogin credentials:")
        print("  Admin:    admin@example.com / admin123")
        print("  Approver: approver@example.com / approver123")
        print("  User:     user@example.com / user123")

        return True


def main():
    parser = argparse.ArgumentParser(
        description="Unified Installer for Databricks Metadata Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python install.py                          # Full interactive install
  python install.py --config config.yaml     # Use config file
  python install.py --dry-run                # Validate without executing
  python install.py --only secrets,schemas   # Run specific steps only
  python install.py --skip deploy            # Skip specific steps
  python install.py --init-config            # Generate config template
        """
    )

    parser.add_argument("--config", "-c", help="Path to configuration file")
    parser.add_argument("--init-config", action="store_true", help="Generate example config file")
    parser.add_argument("--dry-run", action="store_true", help="Validate without making changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--only", help="Run only these steps (comma-separated)")
    parser.add_argument("--skip", help="Skip these steps (comma-separated)")

    # Individual config overrides
    parser.add_argument("--host", help="Databricks workspace URL")
    parser.add_argument("--token", help="Databricks PAT token")
    parser.add_argument("--warehouse-id", help="SQL Warehouse ID")
    parser.add_argument("--catalog", help="Unity Catalog name")
    parser.add_argument("--scope", help="Secret scope name")
    parser.add_argument("--database-url", help="PostgreSQL connection URL")
    parser.add_argument("--app-name", help="Databricks App name")

    args = parser.parse_args()

    # Handle --init-config
    if args.init_config:
        config_path = "install_config.yaml"
        generate_example_config(config_path)
        print(f"Generated example configuration: {config_path}")
        print("Edit this file and run: python install.py --config install_config.yaml")
        return 0

    # Load configuration
    loader = ConfigLoader()

    # Load from file if specified
    if args.config:
        loader.load_from_file(args.config)

    # Load from environment
    loader.load_from_env()

    # Load from CLI args
    loader.load_from_args(args)

    # Validate configuration
    errors = loader.validate()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        return 1

    config = loader.get_config()

    # Parse only/skip
    only = args.only.split(",") if args.only else None
    skip = args.skip.split(",") if args.skip else None

    # Run installer
    installer = MetadataManagerInstaller(
        config=config,
        verbose=args.verbose,
        dry_run=args.dry_run
    )

    try:
        success = installer.run(only=only, skip=skip)
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
        return 1
    except Exception as e:
        print(f"\nInstallation failed with error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
