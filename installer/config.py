"""
Configuration management for Metadata Manager installer.

Handles loading, validation, and merging of configuration from:
- YAML config files
- Environment variables
- CLI arguments
"""

import os
import yaml
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from pathlib import Path


@dataclass
class DatabricksConfig:
    """Databricks workspace configuration"""
    host: str = ""
    token: str = ""
    warehouse_id: str = ""


@dataclass
class CatalogConfig:
    """Unity Catalog configuration"""
    name: str = "arao"
    schema_primary: str = "metadata_manager"
    schema_test: str = "metadata_test"
    create_test_schema: bool = True


@dataclass
class SecretsConfig:
    """Databricks secret scope configuration"""
    scope_name: str = "metadata-manager-secrets"
    databricks_token: str = ""
    databricks_host: str = ""
    secret_key: str = ""
    database_url: str = ""


@dataclass
class ServicePrincipalConfig:
    """Service principal configuration"""
    name: str = "metadata-manager"


@dataclass
class DatabaseConfig:
    """Neon PostgreSQL configuration"""
    url: str = ""
    run_migrations: bool = True
    seed_data: bool = True


@dataclass
class DeploymentConfig:
    """Databricks Apps deployment configuration"""
    app_name: str = "metadata-manager"
    workspace_path: str = ""


@dataclass
class OptionsConfig:
    """Installation options"""
    skip_existing: bool = True
    verify_structure: bool = True
    interactive: bool = True
    verbose: bool = False
    dry_run: bool = False


@dataclass
class InstallConfig:
    """Complete installation configuration"""
    databricks: DatabricksConfig = field(default_factory=DatabricksConfig)
    catalog: CatalogConfig = field(default_factory=CatalogConfig)
    secrets: SecretsConfig = field(default_factory=SecretsConfig)
    service_principal: ServicePrincipalConfig = field(default_factory=ServicePrincipalConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    deployment: DeploymentConfig = field(default_factory=DeploymentConfig)
    options: OptionsConfig = field(default_factory=OptionsConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "databricks": asdict(self.databricks),
            "catalog": {
                "name": self.catalog.name,
                "schemas": {
                    "primary": self.catalog.schema_primary,
                    "test": self.catalog.schema_test,
                },
                "create_test_schema": self.catalog.create_test_schema,
            },
            "secrets": {
                "scope_name": self.secrets.scope_name,
            },
            "service_principal": asdict(self.service_principal),
            "database": asdict(self.database),
            "deployment": asdict(self.deployment),
            "options": asdict(self.options),
        }


class ConfigLoader:
    """Loads and merges configuration from multiple sources"""

    ENV_MAPPINGS = {
        "DATABRICKS_HOST": ("databricks", "host"),
        "DATABRICKS_TOKEN": ("databricks", "token"),
        "DATABRICKS_WAREHOUSE_ID": ("databricks", "warehouse_id"),
        "DATABASE_URL": ("database", "url"),
        "SECRET_SCOPE_NAME": ("secrets", "scope_name"),
        "CATALOG_NAME": ("catalog", "name"),
        "SERVICE_PRINCIPAL_NAME": ("service_principal", "name"),
        "APP_NAME": ("deployment", "app_name"),
    }

    def __init__(self):
        self.config = InstallConfig()

    def load_from_file(self, path: str) -> "ConfigLoader":
        """Load configuration from YAML file"""
        config_path = Path(path)
        if not config_path.exists():
            return self

        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}

        self._apply_dict(data)
        return self

    def load_from_env(self) -> "ConfigLoader":
        """Load configuration from environment variables"""
        for env_var, (section, key) in self.ENV_MAPPINGS.items():
            value = os.getenv(env_var)
            if value:
                self._set_nested(section, key, value)
        return self

    def load_from_args(self, args: Any) -> "ConfigLoader":
        """Load configuration from CLI arguments"""
        if hasattr(args, "config") and args.config:
            self.load_from_file(args.config)

        # Map CLI args to config
        arg_mappings = {
            "host": ("databricks", "host"),
            "token": ("databricks", "token"),
            "warehouse_id": ("databricks", "warehouse_id"),
            "catalog": ("catalog", "name"),
            "scope": ("secrets", "scope_name"),
            "database_url": ("database", "url"),
            "app_name": ("deployment", "app_name"),
            "verbose": ("options", "verbose"),
            "dry_run": ("options", "dry_run"),
        }

        for arg_name, (section, key) in arg_mappings.items():
            if hasattr(args, arg_name):
                value = getattr(args, arg_name)
                if value is not None:
                    self._set_nested(section, key, value)

        return self

    def _apply_dict(self, data: Dict[str, Any]) -> None:
        """Apply dictionary data to config"""
        if "databricks" in data:
            db = data["databricks"]
            if "host" in db:
                self.config.databricks.host = db["host"]
            if "token" in db:
                self.config.databricks.token = db["token"]
            if "warehouse_id" in db:
                self.config.databricks.warehouse_id = db["warehouse_id"]

        if "catalog" in data:
            cat = data["catalog"]
            if "name" in cat:
                self.config.catalog.name = cat["name"]
            if "schemas" in cat:
                schemas = cat["schemas"]
                if "primary" in schemas:
                    self.config.catalog.schema_primary = schemas["primary"]
                if "test" in schemas:
                    self.config.catalog.schema_test = schemas["test"]
            if "create_test_schema" in cat:
                self.config.catalog.create_test_schema = cat["create_test_schema"]

        if "secrets" in data:
            sec = data["secrets"]
            if "scope_name" in sec:
                self.config.secrets.scope_name = sec["scope_name"]

        if "service_principal" in data:
            sp = data["service_principal"]
            if "name" in sp:
                self.config.service_principal.name = sp["name"]

        if "database" in data:
            db = data["database"]
            if "url" in db:
                self.config.database.url = db["url"]
            if "run_migrations" in db:
                self.config.database.run_migrations = db["run_migrations"]
            if "seed_data" in db:
                self.config.database.seed_data = db["seed_data"]

        if "deployment" in data:
            dep = data["deployment"]
            if "app_name" in dep:
                self.config.deployment.app_name = dep["app_name"]
            if "workspace_path" in dep:
                self.config.deployment.workspace_path = dep["workspace_path"]

        if "options" in data:
            opt = data["options"]
            if "skip_existing" in opt:
                self.config.options.skip_existing = opt["skip_existing"]
            if "verify_structure" in opt:
                self.config.options.verify_structure = opt["verify_structure"]
            if "interactive" in opt:
                self.config.options.interactive = opt["interactive"]
            if "verbose" in opt:
                self.config.options.verbose = opt["verbose"]

    def _set_nested(self, section: str, key: str, value: Any) -> None:
        """Set a nested config value"""
        section_obj = getattr(self.config, section, None)
        if section_obj and hasattr(section_obj, key):
            setattr(section_obj, key, value)

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []

        # These will be prompted interactively if missing
        # So we don't treat them as errors here
        # Just validate format if present

        if self.config.databricks.host and not self.config.databricks.host.startswith("https://"):
            errors.append("Databricks host must start with https://")

        if self.config.databricks.token and not self.config.databricks.token.startswith("dapi"):
            errors.append("Databricks token should start with 'dapi'")

        if self.config.database.url and not self.config.database.url.startswith("postgresql://"):
            errors.append("Database URL must start with postgresql://")

        return errors

    def get_missing_required(self) -> List[str]:
        """Get list of missing required values that need to be prompted"""
        missing = []

        if not self.config.databricks.host:
            missing.append("databricks_host")
        if not self.config.databricks.token:
            missing.append("databricks_token")
        if not self.config.databricks.warehouse_id:
            missing.append("warehouse_id")
        if not self.config.database.url:
            missing.append("database_url")

        return missing

    def save_to_file(self, path: str) -> None:
        """Save current configuration to YAML file"""
        # Don't save sensitive values
        data = self.config.to_dict()
        # Clear sensitive fields
        data["databricks"]["token"] = ""
        data["database"]["url"] = ""

        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    def get_config(self) -> InstallConfig:
        """Get the loaded configuration"""
        return self.config


def generate_example_config(path: str) -> None:
    """Generate an example configuration file"""
    example = """# Metadata Manager Installation Configuration
# Generated by: python install.py --init-config

version: "1.0"

# Databricks Configuration
databricks:
  host: ""                              # e.g., https://your-workspace.cloud.databricks.com
  warehouse_id: ""                      # SQL warehouse ID for DDL execution
  # token: ""                           # PAT token - prompted securely if not in environment

# Unity Catalog Configuration
catalog:
  name: "arao"                          # Default catalog name
  schemas:
    primary: "metadata_manager"         # Main application schema
    test: "metadata_test"               # Test data schema
  create_test_schema: true              # Whether to create test schema

# Service Principal Configuration
service_principal:
  name: "metadata-manager"              # App's service principal name

# Secret Scope Configuration
secrets:
  scope_name: "metadata-manager-secrets"

# Neon PostgreSQL Configuration
database:
  # url: ""                             # Connection string - prompted securely if not in environment
  run_migrations: true                  # Run Alembic migrations
  seed_data: true                       # Seed initial admin user

# Deployment Configuration
deployment:
  app_name: "metadata-manager"
  workspace_path: ""                    # Auto-detected from user email

# Installation Options
options:
  skip_existing: true                   # Skip objects that already exist
  verify_structure: true                # Verify existing objects match expected schema
  interactive: true                     # Prompt for missing values
  verbose: false                        # Show detailed output
"""
    with open(path, "w") as f:
        f.write(example)
