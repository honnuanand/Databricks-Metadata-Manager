#!/usr/bin/env python3
"""
Setup secrets for Metadata Manager in Databricks
"""

import subprocess
import getpass
import secrets as py_secrets
import sys

def run_command(command):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def get_workspace_url():
    """Get workspace URL from Databricks CLI"""
    exit_code, stdout, stderr = run_command(["databricks", "auth", "env", "--profile", "DEFAULT"])
    if exit_code == 0:
        for line in stdout.split('\n'):
            if 'DATABRICKS_HOST' in line and '=' in line:
                return line.split('=')[1].strip().strip('"').strip(',')
    return None

def add_secret(scope, key, value):
    """Add a secret to the scope"""
    exit_code, stdout, stderr = run_command([
        "databricks", "secrets", "put-secret",
        scope, key,
        "--string-value", value
    ])

    if exit_code == 0:
        print(f"✅ Added secret: {key}")
        return True
    else:
        print(f"❌ Failed to add secret {key}: {stderr}")
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Setup secrets for Metadata Manager")
    parser.add_argument("--scope", default="metadata-manager-secrets", help="Secret scope name")
    args = parser.parse_args()

    scope_name = args.scope

    print("🔐 Setting up secrets for Metadata Manager")
    print("=" * 60)

    # Get workspace URL automatically
    workspace_url = get_workspace_url()
    if workspace_url:
        print(f"📍 Detected workspace: {workspace_url}")
    else:
        workspace_url = input("Enter Databricks workspace URL: ").strip()

    # Get Databricks token
    print("\n1. Databricks Token")
    print("   This token will be used by the app to access Databricks APIs")
    databricks_token = getpass.getpass("   Enter Databricks personal access token: ").strip()

    if not databricks_token:
        print("❌ Databricks token is required")
        sys.exit(1)

    # Generate secret key for JWT
    print("\n2. Secret Key (JWT)")
    print("   Generating random secret key for JWT token signing...")
    secret_key = py_secrets.token_urlsafe(32)
    print(f"   Generated: {secret_key[:16]}...")

    # Add all secrets
    print(f"\n📝 Adding secrets to scope: {scope_name}")
    print("-" * 60)

    success = True
    success &= add_secret(scope_name, "databricks-token", databricks_token)
    success &= add_secret(scope_name, "databricks-host", workspace_url)
    success &= add_secret(scope_name, "secret-key", secret_key)

    if success:
        print("\n✅ All secrets added successfully!")
        print(f"\n📋 Secret scope: {scope_name}")
        print("   Secrets:")
        print("   - databricks-token")
        print("   - databricks-host")
        print("   - secret-key")
        print("\n💡 You can now deploy the app using:")
        print(f"   python3 deploy_to_databricks.py --skip-secrets")
    else:
        print("\n❌ Some secrets failed to add")
        sys.exit(1)

if __name__ == "__main__":
    main()
