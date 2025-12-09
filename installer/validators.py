"""
Input validation for Metadata Manager installer.

Provides validation functions for all user inputs including:
- Databricks workspace URLs
- PAT tokens
- PostgreSQL connection strings
- Catalog/schema names
- Warehouse IDs
"""

import re
from typing import Tuple
from urllib.parse import urlparse


def validate_databricks_host(url: str) -> Tuple[bool, str]:
    """
    Validate Databricks workspace URL.

    Args:
        url: The URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "Databricks host URL is required"

    if not url.startswith("https://"):
        return False, "Databricks host must start with https://"

    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return False, "Invalid URL format"

        # Check for common Databricks patterns
        valid_patterns = [
            r".*\.cloud\.databricks\.com$",
            r".*\.azuredatabricks\.net$",
            r".*\.gcp\.databricks\.com$",
            r".*\.databricks\.com$",
        ]

        is_databricks = any(re.match(pattern, parsed.netloc) for pattern in valid_patterns)
        if not is_databricks:
            return False, f"URL doesn't appear to be a Databricks workspace: {parsed.netloc}"

        return True, ""
    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


def validate_databricks_token(token: str) -> Tuple[bool, str]:
    """
    Validate Databricks Personal Access Token.

    Args:
        token: The PAT token to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not token:
        return False, "Databricks token is required"

    # PAT tokens typically start with 'dapi'
    if not token.startswith("dapi"):
        return False, "Databricks PAT token should start with 'dapi'"

    # Typical length is around 30-40 characters
    if len(token) < 20:
        return False, "Token appears too short"

    # Check for valid characters (alphanumeric and some special chars)
    if not re.match(r"^dapi[a-zA-Z0-9_-]+$", token):
        return False, "Token contains invalid characters"

    return True, ""


def validate_postgres_url(url: str) -> Tuple[bool, str]:
    """
    Validate PostgreSQL connection string.

    Args:
        url: The connection string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "Database URL is required"

    if not url.startswith("postgresql://") and not url.startswith("postgres://"):
        return False, "Database URL must start with postgresql:// or postgres://"

    try:
        parsed = urlparse(url)

        if not parsed.username:
            return False, "Database URL must include username"

        if not parsed.hostname:
            return False, "Database URL must include hostname"

        if not parsed.path or parsed.path == "/":
            return False, "Database URL must include database name"

        return True, ""
    except Exception as e:
        return False, f"Invalid database URL: {str(e)}"


def validate_catalog_name(name: str) -> Tuple[bool, str]:
    """
    Validate Unity Catalog name.

    Args:
        name: The catalog name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Catalog name is required"

    # Catalog names must follow Databricks naming conventions
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", name):
        return False, "Catalog name must start with a letter and contain only letters, numbers, and underscores"

    if len(name) > 255:
        return False, "Catalog name too long (max 255 characters)"

    return True, ""


def validate_schema_name(name: str) -> Tuple[bool, str]:
    """
    Validate Unity Catalog schema name.

    Args:
        name: The schema name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Schema name is required"

    # Schema names must follow Databricks naming conventions
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", name):
        return False, "Schema name must start with a letter and contain only letters, numbers, and underscores"

    if len(name) > 255:
        return False, "Schema name too long (max 255 characters)"

    return True, ""


def validate_warehouse_id(warehouse_id: str) -> Tuple[bool, str]:
    """
    Validate Databricks SQL Warehouse ID.

    Args:
        warehouse_id: The warehouse ID to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not warehouse_id:
        return False, "Warehouse ID is required"

    # Warehouse IDs are typically 16 hex characters
    if not re.match(r"^[a-f0-9]{16}$", warehouse_id.lower()):
        return False, "Warehouse ID should be a 16-character hexadecimal string"

    return True, ""


def validate_scope_name(name: str) -> Tuple[bool, str]:
    """
    Validate Databricks secret scope name.

    Args:
        name: The scope name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Scope name is required"

    # Scope names can contain alphanumeric, dashes, underscores
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        return False, "Scope name can only contain letters, numbers, dashes, and underscores"

    if len(name) > 128:
        return False, "Scope name too long (max 128 characters)"

    return True, ""


def validate_service_principal_name(name: str) -> Tuple[bool, str]:
    """
    Validate service principal name.

    Args:
        name: The service principal name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Service principal name is required"

    # Service principal names can contain alphanumeric, dashes, underscores, spaces
    if not re.match(r"^[a-zA-Z0-9_\- ]+$", name):
        return False, "Service principal name contains invalid characters"

    return True, ""


def validate_app_name(name: str) -> Tuple[bool, str]:
    """
    Validate Databricks App name.

    Args:
        name: The app name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "App name is required"

    # App names should be lowercase with dashes
    if not re.match(r"^[a-z][a-z0-9-]*$", name):
        return False, "App name must be lowercase, start with a letter, and contain only letters, numbers, and dashes"

    if len(name) > 63:
        return False, "App name too long (max 63 characters)"

    return True, ""
