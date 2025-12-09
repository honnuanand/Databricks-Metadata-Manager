"""
Databricks Apps deployment for Metadata Manager installer.

Handles:
- Frontend build
- Backend packaging
- App deployment to Databricks
"""

import os
import subprocess
import shutil
import json
import time
from typing import Tuple, List, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DeploymentResult:
    """Result of deployment operation"""
    success: bool
    message: str
    app_url: Optional[str] = None


class AppDeployer:
    """Handles Databricks Apps deployment"""

    def __init__(
        self,
        app_name: str = "metadata-manager",
        secret_scope: str = "metadata-manager-secrets",
        workspace_path: str = None,
        verbose: bool = False
    ):
        self.app_name = app_name
        self.secret_scope = secret_scope
        self.workspace_path = workspace_path
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        self.frontend_path = self.project_root / "front-end"
        self.backend_path = self.project_root / "backend"

        # Auto-detect workspace path if not provided
        if not self.workspace_path:
            self._detect_workspace_path()

    def run_command(self, command: List[str], cwd: str = None) -> Tuple[int, str, str]:
        """Run a shell command and return exit code, stdout, stderr"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                cwd=cwd,
                timeout=600  # 10 minute timeout for build commands
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except Exception as e:
            return 1, "", str(e)

    def _detect_workspace_path(self):
        """Detect workspace path from current user"""
        exit_code, stdout, stderr = self.run_command([
            "databricks", "current-user", "me", "--output", "json"
        ])

        if exit_code == 0:
            try:
                user_info = json.loads(stdout)
                user_email = user_info.get("userName") or user_info.get("user_name")
                if user_email:
                    self.workspace_path = f"/Workspace/Users/{user_email}/{self.app_name}"
            except json.JSONDecodeError:
                pass

        if not self.workspace_path:
            self.workspace_path = f"/Workspace/Users/unknown/{self.app_name}"

    def build_frontend(self) -> Tuple[bool, str]:
        """Build the React frontend"""
        if not self.frontend_path.exists():
            return False, f"Frontend path not found: {self.frontend_path}"

        # Check if node_modules exists
        node_modules = self.frontend_path / "node_modules"
        if not node_modules.exists():
            exit_code, stdout, stderr = self.run_command(
                ["npm", "install"],
                cwd=str(self.frontend_path)
            )
            if exit_code != 0:
                return False, f"npm install failed: {stderr}"

        # Build
        exit_code, stdout, stderr = self.run_command(
            ["npm", "run", "build"],
            cwd=str(self.frontend_path)
        )

        if exit_code != 0:
            return False, f"Frontend build failed: {stderr}"

        return True, "Frontend built successfully"

    def copy_static_files(self) -> Tuple[bool, str]:
        """Copy built frontend to backend static directory"""
        dist_path = self.frontend_path / "dist"
        static_path = self.backend_path / "static"

        if not dist_path.exists():
            return False, f"Frontend dist not found: {dist_path}"

        # Remove existing static directory
        if static_path.exists():
            shutil.rmtree(static_path)

        # Copy dist to static
        try:
            shutil.copytree(dist_path, static_path)
            return True, "Static files copied"
        except Exception as e:
            return False, f"Failed to copy static files: {e}"

    def package_backend(
        self,
        database_url: str = None,
        secret_key: str = None
    ) -> Tuple[bool, str]:
        """Package the backend for deployment"""
        build_dir = self.backend_path / "build"

        # Remove existing build directory
        if build_dir.exists():
            shutil.rmtree(build_dir)

        build_dir.mkdir(parents=True)

        # Files/directories to exclude
        exclude_patterns = [
            "venv", "venv.*", ".venv", "env", ".env",
            "__pycache__", "*.pyc", "*.pyo", "*.pyd",
            ".pytest_cache", "test_*.py", "tests",
            "*.log",
            ".env_template", "Makefile",
            "build", "dist", "*.egg-info",
            "node_modules", ".git", ".gitignore",
            ".DS_Store", "Thumbs.db",
        ]

        def should_exclude(item):
            import fnmatch
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(item, pattern):
                    return True
            return False

        # Copy backend files
        for item in os.listdir(self.backend_path):
            if not should_exclude(item) and not item.startswith('.'):
                src = self.backend_path / item
                dst = build_dir / item
                if src.is_dir():
                    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*exclude_patterns))
                else:
                    shutil.copy2(src, dst)

        # Generate app.yaml
        app_yaml_content = self._generate_app_yaml(database_url, secret_key)
        app_yaml_path = build_dir / "app.yaml"
        with open(app_yaml_path, 'w') as f:
            f.write(app_yaml_content)

        return True, "Backend packaged successfully"

    def _generate_app_yaml(self, database_url: str = None, secret_key: str = None) -> str:
        """Generate app.yaml for Databricks Apps"""
        lines = [
            'command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]',
            '',
            '# Disable Databricks SSO to use custom authentication',
            'auth:',
            '  enabled: false',
            '',
            'env:',
            '  - name: ENV',
            '    value: "production"',
            '  - name: PORT',
            '    value: "8000"',
            '  - name: DEBUG',
            '    value: "False"',
        ]

        # Add DATABASE_URL
        if database_url:
            # Inject as direct value since valueFrom doesn't work reliably
            lines.append('  - name: DATABASE_URL')
            lines.append(f'    value: "{database_url}"')

        # Add SECRET_KEY
        if secret_key:
            lines.append('  - name: SECRET_KEY')
            lines.append(f'    value: "{secret_key}"')

        # Add Databricks credentials from secret scope
        lines.append('  - name: DATABRICKS_HOST')
        lines.append(f'    valueFrom: {self.secret_scope}/databricks-host')
        lines.append('  - name: DATABRICKS_TOKEN')
        lines.append(f'    valueFrom: {self.secret_scope}/databricks-token')

        return '\n'.join(lines)

    def upload_to_workspace(self) -> Tuple[bool, str]:
        """Upload packaged app to Databricks workspace"""
        build_dir = self.backend_path / "build"

        if not build_dir.exists():
            return False, "Build directory not found. Run package_backend first."

        exit_code, stdout, stderr = self.run_command([
            "databricks", "workspace", "import-dir",
            str(build_dir), self.workspace_path, "--overwrite"
        ])

        if exit_code != 0:
            return False, f"Failed to upload to workspace: {stderr}"

        return True, f"Uploaded to {self.workspace_path}"

    def create_app(self) -> Tuple[bool, str]:
        """Create or update the Databricks App"""
        # Check if app exists
        exit_code, stdout, stderr = self.run_command([
            "databricks", "apps", "get", self.app_name, "--output", "json"
        ])

        app_exists = exit_code == 0

        if not app_exists:
            # Create new app
            exit_code, stdout, stderr = self.run_command([
                "databricks", "apps", "create", self.app_name
            ])

            if exit_code != 0 and "already exists" not in stderr:
                return False, f"Failed to create app: {stderr}"

        return True, f"App '{self.app_name}' ready"

    def deploy_app(self) -> Tuple[bool, str]:
        """Deploy the app"""
        exit_code, stdout, stderr = self.run_command([
            "databricks", "apps", "deploy", self.app_name,
            "--source-code-path", self.workspace_path
        ])

        if exit_code != 0:
            return False, f"Deployment failed: {stderr}"

        return True, "App deployed"

    def wait_for_deployment(self, timeout: int = 300) -> DeploymentResult:
        """Wait for app to be running and return URL"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            exit_code, stdout, stderr = self.run_command([
                "databricks", "apps", "get", self.app_name, "--output", "json"
            ])

            if exit_code == 0:
                try:
                    app_info = json.loads(stdout)
                    state = app_info.get("app_status", {}).get("state", "")
                    app_url = app_info.get("url", "")

                    if state == "RUNNING":
                        return DeploymentResult(
                            success=True,
                            message="App is running",
                            app_url=app_url
                        )
                    elif state == "FAILED":
                        return DeploymentResult(
                            success=False,
                            message="App deployment failed"
                        )

                except json.JSONDecodeError:
                    pass

            time.sleep(10)

        return DeploymentResult(
            success=False,
            message=f"Deployment timed out after {timeout} seconds"
        )

    def delete_app(self) -> Tuple[bool, str]:
        """Delete the app (for hard redeploy)"""
        exit_code, stdout, stderr = self.run_command([
            "databricks", "apps", "delete", self.app_name
        ])

        if exit_code != 0 and "not found" not in stderr.lower():
            return False, f"Failed to delete app: {stderr}"

        return True, f"Deleted app '{self.app_name}'"

    def wait_for_deletion(self, timeout: int = 300) -> bool:
        """Wait for app deletion to complete"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            exit_code, stdout, stderr = self.run_command([
                "databricks", "apps", "list"
            ])

            if exit_code == 0 and self.app_name not in stdout:
                return True

            time.sleep(5)

        return False

    def deploy_full(
        self,
        database_url: str = None,
        secret_key: str = None,
        hard_redeploy: bool = False,
        dry_run: bool = False
    ) -> Tuple[bool, List[str]]:
        """
        Full deployment workflow.

        Returns:
            Tuple of (success, list of messages)
        """
        messages = []

        if dry_run:
            messages.append("[DRY RUN] Would build frontend")
            messages.append("[DRY RUN] Would copy static files")
            messages.append("[DRY RUN] Would package backend")
            messages.append("[DRY RUN] Would upload to workspace")
            messages.append("[DRY RUN] Would deploy app")
            return True, messages

        # Hard redeploy: delete existing app first
        if hard_redeploy:
            messages.append("Hard redeploy: deleting existing app...")
            success, msg = self.delete_app()
            messages.append(msg)
            if success:
                if self.wait_for_deletion():
                    messages.append("App deleted successfully")
                else:
                    messages.append("Warning: App deletion may not have completed")

        # Build frontend
        success, msg = self.build_frontend()
        messages.append(msg)
        if not success:
            return False, messages

        # Copy static files
        success, msg = self.copy_static_files()
        messages.append(msg)
        if not success:
            return False, messages

        # Package backend
        success, msg = self.package_backend(database_url, secret_key)
        messages.append(msg)
        if not success:
            return False, messages

        # Upload to workspace
        success, msg = self.upload_to_workspace()
        messages.append(msg)
        if not success:
            return False, messages

        # Create app
        success, msg = self.create_app()
        messages.append(msg)
        if not success:
            return False, messages

        # Deploy
        success, msg = self.deploy_app()
        messages.append(msg)
        if not success:
            return False, messages

        # Wait for deployment
        result = self.wait_for_deployment()
        messages.append(result.message)
        if result.app_url:
            messages.append(f"App URL: {result.app_url}")

        return result.success, messages

    def cleanup(self):
        """Clean up build artifacts"""
        build_dir = self.backend_path / "build"
        if build_dir.exists():
            shutil.rmtree(build_dir)
