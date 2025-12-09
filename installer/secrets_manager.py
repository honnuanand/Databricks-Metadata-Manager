"""
Databricks secret scope management for Metadata Manager installer.

Handles creation and management of Databricks secret scopes:
- Create/verify secret scopes
- Add/update secrets
- Generate secure secret keys
"""

import subprocess
import secrets as py_secrets
import json
import base64
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass


@dataclass
class SecretInfo:
    """Information about a secret"""
    key: str
    description: str
    required: bool = True
    auto_generate: bool = False


class SecretsManager:
    """Manages Databricks secret scopes and secrets"""

    REQUIRED_SECRETS = [
        SecretInfo("databricks-token", "Databricks PAT token for API access", required=True),
        SecretInfo("databricks-host", "Databricks workspace URL", required=True),
        SecretInfo("secret-key", "JWT signing key for authentication", required=True, auto_generate=True),
        SecretInfo("database-url", "Neon PostgreSQL connection string", required=True),
    ]

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def run_command(self, command: List[str]) -> Tuple[int, str, str]:
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

    def check_scope_exists(self, scope_name: str) -> bool:
        """Check if a secret scope exists"""
        exit_code, stdout, stderr = self.run_command([
            "databricks", "secrets", "list-scopes"
        ])

        if exit_code != 0:
            return False

        # Parse output to find scope
        lines = stdout.strip().split('\n')
        for line in lines[1:]:  # Skip header
            if line.strip().startswith(scope_name):
                return True

        return False

    def create_scope(self, scope_name: str) -> Tuple[bool, str]:
        """Create a new secret scope"""
        if self.check_scope_exists(scope_name):
            return True, f"Scope '{scope_name}' already exists"

        exit_code, stdout, stderr = self.run_command([
            "databricks", "secrets", "create-scope", scope_name
        ])

        if exit_code != 0:
            # Check if it already exists (race condition)
            if "already exists" in stderr.lower():
                return True, f"Scope '{scope_name}' already exists"
            return False, f"Failed to create scope: {stderr}"

        return True, f"Created scope '{scope_name}'"

    def list_secrets(self, scope_name: str) -> List[str]:
        """List all secrets in a scope"""
        exit_code, stdout, stderr = self.run_command([
            "databricks", "secrets", "list-secrets", scope_name
        ])

        if exit_code != 0:
            return []

        secrets = []
        lines = stdout.strip().split('\n')
        for line in lines[1:]:  # Skip header
            parts = line.split()
            if parts:
                secrets.append(parts[0])

        return secrets

    def put_secret(self, scope_name: str, key: str, value: str) -> Tuple[bool, str]:
        """Add or update a secret in a scope"""
        exit_code, stdout, stderr = self.run_command([
            "databricks", "secrets", "put-secret",
            scope_name, key,
            "--string-value", value
        ])

        if exit_code != 0:
            return False, f"Failed to add secret '{key}': {stderr}"

        return True, f"Added secret '{key}'"

    def get_secret(self, scope_name: str, key: str) -> Optional[str]:
        """Get a secret value from a scope (base64 decoded)"""
        exit_code, stdout, stderr = self.run_command([
            "databricks", "secrets", "get-secret",
            scope_name, key,
            "--output", "json"
        ])

        if exit_code != 0:
            return None

        try:
            secret_data = json.loads(stdout)
            # Databricks returns base64-encoded value
            encoded_value = secret_data.get("value", "")
            return base64.b64decode(encoded_value).decode('utf-8')
        except (json.JSONDecodeError, Exception):
            return None

    def delete_secret(self, scope_name: str, key: str) -> Tuple[bool, str]:
        """Delete a secret from a scope"""
        exit_code, stdout, stderr = self.run_command([
            "databricks", "secrets", "delete-secret",
            scope_name, key
        ])

        if exit_code != 0:
            return False, f"Failed to delete secret '{key}': {stderr}"

        return True, f"Deleted secret '{key}'"

    def generate_secret_key(self) -> str:
        """Generate a secure random secret key for JWT signing"""
        return py_secrets.token_urlsafe(32)

    def verify_secrets(self, scope_name: str) -> Dict[str, bool]:
        """Verify all required secrets exist in a scope"""
        existing_secrets = self.list_secrets(scope_name)
        verification = {}

        for secret_info in self.REQUIRED_SECRETS:
            verification[secret_info.key] = secret_info.key in existing_secrets

        return verification

    def setup_secrets(
        self,
        scope_name: str,
        databricks_token: str,
        databricks_host: str,
        database_url: str,
        secret_key: str = None,
        dry_run: bool = False
    ) -> Tuple[bool, List[str]]:
        """
        Set up all required secrets in a scope.

        Args:
            scope_name: Name of the secret scope
            databricks_token: Databricks PAT token
            databricks_host: Databricks workspace URL
            database_url: PostgreSQL connection string
            secret_key: JWT secret key (auto-generated if not provided)
            dry_run: If True, don't actually create secrets

        Returns:
            Tuple of (success, list of messages)
        """
        messages = []

        # Generate secret key if not provided
        if not secret_key:
            secret_key = self.generate_secret_key()
            messages.append(f"Generated new secret key: {secret_key[:16]}...")

        if dry_run:
            messages.append(f"[DRY RUN] Would create scope: {scope_name}")
            messages.append(f"[DRY RUN] Would add secrets: databricks-token, databricks-host, secret-key, database-url")
            return True, messages

        # Create scope if needed
        success, msg = self.create_scope(scope_name)
        messages.append(msg)
        if not success:
            return False, messages

        # Add all secrets
        secrets_to_add = [
            ("databricks-token", databricks_token),
            ("databricks-host", databricks_host),
            ("secret-key", secret_key),
            ("database-url", database_url),
        ]

        all_success = True
        for key, value in secrets_to_add:
            success, msg = self.put_secret(scope_name, key, value)
            messages.append(msg)
            if not success:
                all_success = False

        return all_success, messages

    def print_secrets_status(self, scope_name: str) -> None:
        """Print status of secrets in a scope"""
        print(f"\nSecrets in scope '{scope_name}':")
        print("-" * 40)

        verification = self.verify_secrets(scope_name)
        for key, exists in verification.items():
            status = "[OK]" if exists else "[MISSING]"
            print(f"  {status} {key}")

        print()

    def get_secrets_for_deployment(self, scope_name: str) -> Dict[str, Optional[str]]:
        """
        Get secrets values for deployment (to inject into app.yaml).

        Note: This retrieves actual secret values - use with caution.
        """
        secrets = {}
        for secret_info in self.REQUIRED_SECRETS:
            secrets[secret_info.key] = self.get_secret(scope_name, secret_info.key)
        return secrets
