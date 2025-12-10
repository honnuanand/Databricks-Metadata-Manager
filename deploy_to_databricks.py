#!/usr/bin/env python3
"""
Databricks Deployment Script for Metadata Manager
Handles CLI setup, secrets management, and app deployment
"""

import os
import sys
import json
import subprocess
import getpass
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import argparse
import fnmatch
import shutil
import time

@dataclass
class SecretConfig:
    """Configuration for a secret"""
    key: str
    value: str
    description: str

@dataclass
class ScopeInfo:
    """Information about a Databricks scope"""
    name: str
    owner: str
    created_at: str
    secret_count: int

class MetadataManagerDeployer:
    def __init__(self, secret_scope: str = "metadata-manager-secrets"):
        self.workspace_url = None
        self.token = None
        self.user_email = None
        self.app_name = "metadata-manager"
        self.app_folder = None  # Will be auto-detected
        self.secret_scope = secret_scope  # Configurable secret scope name

        # Auto-detect workspace info
        self._auto_detect_workspace_info()

        # Required secrets for the application
        self.required_secrets = [
            SecretConfig("databricks-token", "", "Databricks personal access token"),
            SecretConfig("databricks-host", "", "Databricks workspace URL"),
            SecretConfig("secret-key", "", "Secret key for JWT token signing"),
        ]

    def _auto_detect_workspace_info(self):
        """Auto-detect workspace URL and user email from Databricks CLI"""
        try:
            # Get workspace URL from auth env (new CLI)
            exit_code, stdout, stderr = self.run_command(["databricks", "auth", "env", "--profile", "DEFAULT"])
            if exit_code == 0 and stdout.strip():
                for line in stdout.split('\n'):
                    if 'DATABRICKS_HOST' in line and '=' in line:
                        # Extract the URL from the line
                        self.workspace_url = line.split('=')[1].strip().strip('"').strip(',')
                        break

            # Get current user email
            exit_code, stdout, stderr = self.run_command(["databricks", "current-user", "me", "--output", "json"])
            if exit_code == 0 and stdout.strip():
                try:
                    user_info = json.loads(stdout)
                    self.user_email = user_info.get("userName") or user_info.get("user_name")

                    # Set app_folder using detected user email
                    if self.user_email and not self.app_folder:
                        self.app_folder = f"/Workspace/Users/{self.user_email}/{self.app_name}"
                except json.JSONDecodeError:
                    pass

            # Fallback if app_folder not set
            if not self.app_folder:
                self.app_folder = f"/Workspace/Users/YOUR_USER@example.com/{self.app_name}"

        except Exception:
            # Silently fail and use defaults
            if not self.app_folder:
                self.app_folder = f"/Workspace/Users/YOUR_USER@example.com/{self.app_name}"

    def run_command(self, command: List[str], capture_output: bool = True, cwd: str = None) -> Tuple[int, str, str]:
        """Run a shell command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                check=False,
                cwd=cwd
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)

    def check_databricks_cli(self) -> bool:
        """Check if Databricks CLI is installed and configured"""
        print("🔍 Checking Databricks CLI...")

        # Check if databricks command exists
        exit_code, stdout, stderr = self.run_command(["databricks", "--version"])
        if exit_code != 0:
            print("❌ Databricks CLI not found. Please install it first:")
            print("   pip install databricks-cli")
            return False

        # Check if configured
        exit_code, stdout, stderr = self.run_command(["databricks", "workspace", "list", "/"])
        if exit_code != 0:
            print("❌ Databricks CLI not configured. Please run:")
            print("   databricks configure --token")
            return False

        print("✅ Databricks CLI is ready")
        print(f"📍 Workspace: {self.workspace_url}")
        print(f"👤 User: {self.user_email}")
        return True

    def get_workspace_info(self) -> bool:
        """Get workspace URL and token from CLI config"""
        try:
            # Get workspace URL
            exit_code, stdout, stderr = self.run_command(["databricks", "workspace", "list", "/"])
            if exit_code != 0:
                return False

            # Try to get workspace URL from auth env
            exit_code, stdout, stderr = self.run_command(["databricks", "auth", "env", "--profile", "DEFAULT"])
            if exit_code == 0:
                for line in stdout.split('\n'):
                    if 'DATABRICKS_HOST' in line and '=' in line:
                        self.workspace_url = line.split('=')[1].strip().strip('"').strip(',')
                        break

            return True
        except Exception as e:
            print(f"❌ Error getting workspace info: {e}")
            return False

    def list_scopes(self) -> List[ScopeInfo]:
        """List all available scopes"""
        print("📋 Fetching available scopes...")

        exit_code, stdout, stderr = self.run_command(["databricks", "secrets", "list-scopes"])
        if exit_code != 0:
            print(f"❌ Error listing scopes: {stderr}")
            return []

        scopes = []
        lines = stdout.strip().split('\n')

        # Skip header line
        for line in lines[1:]:
            if line.strip():
                parts = line.split()
                if len(parts) >= 3:
                    scope_name = parts[0]
                    owner = parts[1]
                    created_at = parts[2]

                    # Get secret count for this scope
                    exit_code, secret_stdout, _ = self.run_command([
                        "databricks", "secrets", "list", "--scope", scope_name
                    ])

                    secret_count = 0
                    if exit_code == 0:
                        secret_lines = secret_stdout.strip().split('\n')
                        secret_count = len(secret_lines) - 1  # Subtract header

                    scopes.append(ScopeInfo(scope_name, owner, created_at, secret_count))

        return scopes

    def select_scope(self, scopes: List[ScopeInfo]) -> Optional[str]:
        """Let user select a scope to use"""
        if not scopes:
            print("❌ No scopes found")
            return None

        print(f"\n📊 Found {len(scopes)} scopes:")
        print("-" * 80)
        print(f"{'#':<3} {'Scope Name':<30} {'Owner':<20} {'Secrets':<8} {'Created':<15}")
        print("-" * 80)

        # Show first 20 scopes
        display_scopes = scopes[:20]
        for i, scope in enumerate(display_scopes, 1):
            print(f"{i:<3} {scope.name:<30} {scope.owner:<20} {scope.secret_count:<8} {scope.created_at:<15}")

        if len(scopes) > 20:
            print(f"... and {len(scopes) - 20} more scopes")

        while True:
            try:
                choice = input(f"\n🎯 Select a scope (1-{len(display_scopes)}) or enter scope name: ").strip()

                # Check if it's a number
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(display_scopes):
                        return display_scopes[idx].name
                    else:
                        print(f"❌ Invalid number. Please enter 1-{len(display_scopes)}")
                        continue

                # Check if it's a scope name
                for scope in scopes:
                    if scope.name == choice:
                        return choice

                print("❌ Invalid scope name. Please try again.")

            except KeyboardInterrupt:
                print("\n❌ Operation cancelled")
                return None

    def create_scope(self) -> Optional[str]:
        """Create a new scope"""
        print("\n🆕 Creating new scope...")

        scope_name = input("Enter scope name (e.g., metadata-manager-secrets): ").strip()
        if not scope_name:
            print("❌ Scope name cannot be empty")
            return None

        exit_code, stdout, stderr = self.run_command([
            "databricks", "secrets", "create-scope", "--scope", scope_name
        ])

        if exit_code == 0:
            print(f"✅ Created scope: {scope_name}")
            return scope_name
        else:
            print(f"❌ Failed to create scope: {stderr}")
            return None

    def get_secret_values(self) -> bool:
        """Get secret values from user input"""
        print("\n🔐 Setting up secrets...")

        for secret in self.required_secrets:
            if secret.key == "databricks-host":
                secret.value = self.workspace_url or input(f"Enter {secret.description}: ").strip()
                print(f"✅ Using workspace URL: {secret.value}")
            elif secret.key == "secret-key":
                # Generate a random secret key for JWT
                import secrets
                secret.value = secrets.token_urlsafe(32)
                print(f"✅ Generated secret key: {secret.value[:16]}...")
            else:
                secret.value = getpass.getpass(f"Enter {secret.description}: ").strip()

            if not secret.value:
                print(f"❌ {secret.description} cannot be empty")
                return False

        return True

    def add_secrets_to_scope(self, scope_name: str) -> bool:
        """Add secrets to the selected scope"""
        print(f"\n🔐 Adding secrets to scope: {scope_name}")

        for secret in self.required_secrets:
            print(f"Adding {secret.key}...")

            exit_code, stdout, stderr = self.run_command([
                "databricks", "secrets", "put",
                "--scope", scope_name,
                "--key", secret.key,
                "--string-value", secret.value
            ])

            if exit_code != 0:
                print(f"❌ Failed to add secret {secret.key}: {stderr}")
                return False

        print("✅ All secrets added successfully")
        return True

    def build_frontend(self) -> bool:
        """Build the React frontend"""
        print("🔨 Building React frontend...")

        # Check if node_modules exists, if not run npm install
        if not os.path.exists("front-end/node_modules"):
            print("📦 Installing frontend dependencies...")
            exit_code, stdout, stderr = self.run_command(
                ["npm", "install"],
                cwd="front-end",
                capture_output=True
            )
            if exit_code != 0:
                print(f"❌ npm install failed: {stderr}")
                return False

        # Build the frontend
        exit_code, stdout, stderr = self.run_command(
            ["npm", "run", "build"],
            cwd="front-end",
            capture_output=True
        )

        if exit_code != 0:
            print(f"❌ Frontend build failed: {stderr}")
            return False

        print("✅ Frontend built successfully")
        return True

    def copy_static_files(self) -> bool:
        """Copy built frontend to backend static directory"""
        print("📁 Copying static files...")

        # Remove existing static directory
        if os.path.exists("backend/static"):
            shutil.rmtree("backend/static")

        # Copy dist to static
        try:
            shutil.copytree("front-end/dist", "backend/static")
            print("✅ Static files copied successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to copy static files: {e}")
            return False

    def package_backend(self) -> bool:
        """Package the backend for deployment"""
        print("📦 Packaging backend...")

        # Create build directory
        build_dir = "backend/build"
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)

        os.makedirs(build_dir)

        # Copy backend files (excluding unnecessary files)
        exclude_patterns = [
            "venv", "venv.*", ".venv", "env", ".env",  # Virtual environments
            "__pycache__", "*.pyc", "*.pyo", "*.pyd",  # Python cache
            ".pytest_cache", "test_*.py", "tests",     # Tests
            "*.log",                                    # Logs
            ".env_template", "Makefile",               # Build files
            "build", "dist", "*.egg-info",             # Build artifacts
            "node_modules", ".git", ".gitignore",      # Dev files
            ".DS_Store", "Thumbs.db",                  # OS files
        ]

        def should_exclude(item):
            """Check if item should be excluded based on patterns"""
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(item, pattern):
                    return True
            return False

        for item in os.listdir("backend"):
            if not should_exclude(item) and not item.startswith('.'):
                src = os.path.join("backend", item)
                dst = os.path.join(build_dir, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*exclude_patterns))
                else:
                    shutil.copy2(src, dst)

        # Get secrets from Databricks (injected as direct values at deploy time)
        import json
        import base64

        secret_key = None
        lakebase_password = None
        databricks_token = None

        print(f"📦 Using secret scope: {self.secret_scope}")

        # Get SECRET_KEY
        try:
            result = subprocess.run(
                ['databricks', 'secrets', 'get-secret', self.secret_scope, 'secret-key', '--output', 'json'],
                capture_output=True,
                text=True,
                check=True
            )
            secret_data = json.loads(result.stdout)
            secret_key = base64.b64decode(secret_data['value']).decode('utf-8')
            print(f"✅ Retrieved SECRET_KEY from secrets")
        except Exception as e:
            print(f"⚠️  Could not retrieve SECRET_KEY from secrets: {e}")

        # Get LAKEBASE_PASSWORD
        try:
            result = subprocess.run(
                ['databricks', 'secrets', 'get-secret', self.secret_scope, 'lakebase-password', '--output', 'json'],
                capture_output=True,
                text=True,
                check=True
            )
            secret_data = json.loads(result.stdout)
            lakebase_password = base64.b64decode(secret_data['value']).decode('utf-8')
            print(f"✅ Retrieved LAKEBASE_PASSWORD from secrets")
        except Exception as e:
            print(f"⚠️  Could not retrieve LAKEBASE_PASSWORD from secrets: {e}")

        # Get DATABRICKS_TOKEN for Unity Catalog access
        try:
            result = subprocess.run(
                ['databricks', 'secrets', 'get-secret', self.secret_scope, 'databricks-token', '--output', 'json'],
                capture_output=True,
                text=True,
                check=True
            )
            secret_data = json.loads(result.stdout)
            databricks_token = base64.b64decode(secret_data['value']).decode('utf-8')
            print(f"✅ Retrieved DATABRICKS_TOKEN from secrets")
        except Exception as e:
            print(f"⚠️  Could not retrieve DATABRICKS_TOKEN from secrets: {e}")

        # Create app.yaml for Databricks Apps
        # Secrets are injected as direct values at deploy time (retrieved above)
        app_yaml_path = os.path.join(build_dir, "app.yaml")
        with open(app_yaml_path, 'w') as f:
            f.write('command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]\n')
            f.write('\n')
            f.write('# Allow anonymous access to the app (use custom JWT authentication)\n')
            f.write('default_source_ip_permissions:\n')
            f.write('  - action: ALLOW\n')
            f.write('    ip_addresses: ["0.0.0.0/0"]\n')
            f.write('\n')
            f.write('env:\n')
            f.write('  - name: ENV\n')
            f.write('    value: "production"\n')
            f.write('  - name: PORT\n')
            f.write('    value: "8000"\n')
            f.write('  - name: DEBUG\n')
            f.write('    value: "False"\n')

            # Lakebase Configuration
            # LAKEBASE_INSTANCE is required for OAuth token generation
            # LAKEBASE_HOST is the PostgreSQL hostname for connections
            f.write('  # Lakebase Database Configuration\n')
            f.write('  - name: LAKEBASE_INSTANCE\n')
            f.write('    value: "arao-lb"\n')
            f.write('  - name: LAKEBASE_HOST\n')
            f.write('    value: "instance-f2a8b56a-7fe2-4c9c-a0a3-7768594a50e5.database.cloud.databricks.com"\n')
            f.write('  - name: LAKEBASE_DATABASE\n')
            f.write('    value: "databricks_postgres"\n')
            f.write('  - name: LAKEBASE_USER\n')
            f.write('    value: "metadata_manager_app"\n')
            f.write('  - name: LAKEBASE_PORT\n')
            f.write('    value: "5432"\n')

            # Inject LAKEBASE_PASSWORD as direct value (retrieved from secrets at deploy time)
            if lakebase_password:
                f.write('  - name: LAKEBASE_PASSWORD\n')
                f.write(f'    value: "{lakebase_password}"\n')
                # Also set DATABASE_URL for backwards compatibility with existing code
                db_url = f"postgresql://metadata_manager_app:{lakebase_password}@instance-f2a8b56a-7fe2-4c9c-a0a3-7768594a50e5.database.cloud.databricks.com:5432/databricks_postgres?sslmode=require"
                f.write('  - name: DATABASE_URL\n')
                f.write(f'    value: "{db_url}"\n')
            else:
                print("❌ LAKEBASE_PASSWORD not available - app may fail to connect to database")

            # Inject SECRET_KEY as direct value (retrieved from secrets at deploy time)
            if secret_key:
                f.write('  - name: SECRET_KEY\n')
                f.write(f'    value: "{secret_key}"\n')

            # Databricks configuration for Unity Catalog access
            f.write('  - name: DATABRICKS_HOST\n')
            f.write('    value: "https://fe-vm-leaps-fe.cloud.databricks.com"\n')
            f.write('  - name: DATABRICKS_WAREHOUSE_PATH\n')
            f.write('    value: "/sql/1.0/warehouses/2dc6b7aacc451bcd"\n')

            # Inject DATABRICKS_TOKEN for Unity Catalog access
            if databricks_token:
                f.write('  - name: DATABRICKS_TOKEN\n')
                f.write(f'    value: "{databricks_token}"\n')
            else:
                print("⚠️  DATABRICKS_TOKEN not available - catalog browsing may not work")

        print("✅ Backend packaged successfully")
        return True

    def import_to_workspace(self) -> bool:
        """Import backend to Databricks workspace"""
        print("📤 Importing to Databricks workspace...")

        exit_code, stdout, stderr = self.run_command([
            "databricks", "workspace", "import-dir",
            "backend/build", self.app_folder, "--overwrite"
        ])

        if exit_code != 0:
            print(f"❌ Failed to import to workspace: {stderr}")
            return False

        print(f"✅ Imported to workspace: {self.app_folder}")
        return True

    def deploy_app(self, scope_name: str = None) -> bool:
        """Deploy the app to Databricks"""
        print("🚀 Deploying app to Databricks...")

        # Create app if it doesn't exist
        exit_code, stdout, stderr = self.run_command([
            "databricks", "apps", "create", self.app_name
        ])

        # Allow deploy to proceed if error is 'already exists'
        if exit_code != 0 and "already exists" not in stderr and "maximum number of apps" not in stderr:
            print(f"⚠️  App creation message: {stderr}")

        # Deploy the app
        exit_code, stdout, stderr = self.run_command([
            "databricks", "apps", "deploy", self.app_name,
            "--source-code-path", self.app_folder
        ])

        if exit_code != 0:
            print(f"❌ Failed to deploy app: {stderr}")
            return False

        print("✅ App deployed successfully!")
        return True

    def wait_for_app_deletion(self, app_name: str, timeout_seconds: int = 300) -> bool:
        """Wait for app deletion to complete"""
        print(f"⏳ Waiting for app deletion to complete...")

        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            # Check if app still exists
            exit_code, stdout, stderr = self.run_command([
                "databricks", "apps", "list"
            ])

            if exit_code != 0:
                print(f"❌ Error checking app list: {stderr}")
                return False

            # Check if our app is still in the list
            if app_name not in stdout:
                print(f"✅ App '{app_name}' has been successfully deleted")
                return True

            print(f"⏳ App '{app_name}' still being deleted... (elapsed: {int(time.time() - start_time)}s)")
            time.sleep(5)

        print(f"❌ Timeout waiting for app deletion after {timeout_seconds} seconds")
        return False

    def delete_app(self, app_name: str) -> bool:
        """Delete an existing app"""
        print(f"🗑️  Deleting app: {app_name}")

        exit_code, stdout, stderr = self.run_command([
            "databricks", "apps", "delete", app_name
        ])

        if exit_code == 0:
            print(f"✅ Deleted app: {app_name}")
            return True
        else:
            print(f"⚠️  Delete message: {stderr}")
            return "not found" in stderr.lower()  # Consider success if app doesn't exist

    def hard_redeploy(self, scope_name: str = None) -> bool:
        """Hard redeploy: delete existing app, wait for deletion, then redeploy"""
        print(f"🔥 Starting HARD REDEPLOY for app: {self.app_name}")
        print("=" * 60)

        # Step 1: Check if app exists and delete it
        print("🔍 Checking if app exists...")
        exit_code, stdout, stderr = self.run_command([
            "databricks", "apps", "list"
        ])

        if exit_code != 0:
            print(f"❌ Error checking app list: {stderr}")
            return False

        app_exists = self.app_name in stdout

        if app_exists:
            print(f"🗑️  App '{self.app_name}' exists. Deleting...")
            if not self.delete_app(self.app_name):
                print("❌ Failed to delete app. Aborting hard redeploy.")
                return False

            # Step 2: Wait for deletion to complete
            if not self.wait_for_app_deletion(self.app_name):
                print("❌ App deletion did not complete in time. Aborting hard redeploy.")
                return False
        else:
            print(f"ℹ️  App '{self.app_name}' does not exist. Proceeding with fresh deployment.")

        # Step 3: Build and package
        print("\n🔨 Building and packaging application...")
        if not self.build_frontend():
            return False
        if not self.copy_static_files():
            return False
        if not self.package_backend():
            return False
        if not self.import_to_workspace():
            return False

        # Step 4: Deploy the app
        print("\n🚀 Deploying fresh app...")
        if not self.deploy_app(scope_name or ""):
            return False

        # Step 5: Get app info
        self.get_app_info()

        print(f"\n🎉 HARD REDEPLOY completed successfully!")
        if scope_name:
            print(f"🔐 Secrets are stored in scope: {scope_name}")

        # Post-deployment instructions for service principal permissions
        print("\n" + "=" * 60)
        print("NEXT STEP: Grant Service Principal Permissions")
        print("=" * 60)
        print("The app needs Unity Catalog permissions to function.")
        print("\n1. Find the service principal name by either:")
        print("   - Checking the app logs in Databricks")
        print("   - Accessing /api/v1/debug/current-user on the app")
        print("\n2. Run the permission grant script:")
        print("   python scripts/grant_permissions.py --principal \"<service-principal-name>\"")
        print("\n   Or run interactively:")
        print("   python scripts/grant_permissions.py")

        return True

    def get_app_info(self) -> bool:
        """Get app information and URL"""
        print("🔍 Getting app information...")

        exit_code, stdout, stderr = self.run_command([
            "databricks", "apps", "get", self.app_name
        ])

        if exit_code != 0:
            print(f"❌ Failed to get app info: {stderr}")
            return False

        try:
            app_info = json.loads(stdout)

            print(f"\n📱 App Information:")
            print(f"   Name: {app_info.get('name', 'N/A')}")
            print(f"   Status: {app_info.get('app_status', {}).get('state', 'N/A')}")
            print(f"   Created: {app_info.get('create_time', 'N/A')}")
            print(f"   Updated: {app_info.get('update_time', 'N/A')}")

            # Get the app URL from the response
            app_url = app_info.get('url', 'N/A')
            if app_url and app_url != 'N/A':
                print(f"\n🌐 App URL: {app_url}")
            else:
                print(f"\n🌐 App URL: Check Databricks Apps dashboard")

            return True
        except json.JSONDecodeError:
            print(f"⚠️  Could not parse app info JSON")
            return False

    def cleanup(self):
        """Clean up temporary files"""
        print("🧹 Cleaning up...")

        # Remove build directory
        if os.path.exists("backend/build"):
            shutil.rmtree("backend/build")

        print("✅ Cleanup completed")

    def deploy(self, hard_redeploy: bool = False, skip_secrets: bool = False):
        """Main deployment workflow"""
        print(f"🚀 Starting Metadata Manager deployment to Databricks")
        print("=" * 60)

        if not self.check_databricks_cli():
            self.cleanup()
            return False

        # Handle secrets setup unless skipped or hard redeploying
        scope_name = None
        if not skip_secrets and not hard_redeploy:
            print("\n🔐 Secret Management")
            print("Do you want to configure secrets for this deployment?")
            print("  1. Use existing scope")
            print("  2. Create new scope")
            print("  3. Skip secrets (use existing)")
            choice = input("Choice (1-3): ").strip()

            if choice == "1":
                scopes = self.list_scopes()
                scope_name = self.select_scope(scopes)
                if scope_name and self.get_secret_values():
                    self.add_secrets_to_scope(scope_name)
            elif choice == "2":
                scope_name = self.create_scope()
                if scope_name and self.get_secret_values():
                    self.add_secrets_to_scope(scope_name)

        # If hard redeploy is requested, skip scope configuration
        if hard_redeploy:
            print("🔥 HARD REDEPLOY mode")
            success = self.hard_redeploy(scope_name)
            self.cleanup()
            return success

        # Normal deployment
        if not self.build_frontend():
            self.cleanup()
            return False
        if not self.copy_static_files():
            self.cleanup()
            return False
        if not self.package_backend():
            self.cleanup()
            return False
        if not self.import_to_workspace():
            self.cleanup()
            return False
        if not self.deploy_app(scope_name):
            self.cleanup()
            return False

        self.get_app_info()
        print("\n🎉 Deployment completed successfully!")

        # Post-deployment instructions for service principal permissions
        print("\n" + "=" * 60)
        print("NEXT STEP: Grant Service Principal Permissions")
        print("=" * 60)
        print("The app needs Unity Catalog permissions to function.")
        print("\n1. Find the service principal name by either:")
        print("   - Checking the app logs in Databricks")
        print("   - Accessing /api/v1/debug/current-user on the app")
        print("\n2. Run the permission grant script:")
        print("   python scripts/grant_permissions.py --principal \"<service-principal-name>\"")
        print("\n   Or run interactively:")
        print("   python scripts/grant_permissions.py")

        self.cleanup()
        return True

def main():
    parser = argparse.ArgumentParser(description="Deploy Metadata Manager to Databricks")
    parser.add_argument("--app-name", default="metadata-manager", help="App name")
    parser.add_argument("--app-folder", default=None, help="App folder in workspace (auto-detected if not provided)")
    parser.add_argument("--hard-redeploy", action="store_true", help="Hard redeploy: delete existing app and redeploy")
    parser.add_argument("--skip-secrets", action="store_true", help="Skip secrets configuration")
    parser.add_argument("--secret-scope", default="metadata-manager-secrets", help="Databricks secret scope name")

    args = parser.parse_args()

    deployer = MetadataManagerDeployer(secret_scope=args.secret_scope)
    deployer.app_name = args.app_name

    # Update app_folder if provided
    if args.app_folder:
        deployer.app_folder = args.app_folder
    elif deployer.user_email:
        deployer.app_folder = f"/Workspace/Users/{deployer.user_email}/{args.app_name}"

    print(f"📍 App will be deployed to: {deployer.app_folder}")

    success = deployer.deploy(hard_redeploy=args.hard_redeploy, skip_secrets=args.skip_secrets)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
