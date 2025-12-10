from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator, computed_field


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Databricks Metadata Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Legacy Database URL (for Neon PostgreSQL or local development)
    DATABASE_URL: Optional[str] = None
    REDIS_URL: str = "redis://localhost:6379/0"

    # Lakebase Configuration (preferred for production)
    LAKEBASE_HOST: Optional[str] = None
    LAKEBASE_PORT: int = 5432
    LAKEBASE_DATABASE: str = "databricks_postgres"
    LAKEBASE_USER: Optional[str] = None
    LAKEBASE_PASSWORD: Optional[str] = None
    # Lakebase instance name (for OAuth token generation)
    LAKEBASE_INSTANCE: Optional[str] = None
    # Use OAuth instead of static password (set to "true" to enable)
    LAKEBASE_USE_OAUTH: bool = False

    @field_validator("LAKEBASE_USE_OAUTH", mode="before")
    @classmethod
    def parse_lakebase_oauth(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return False

    @computed_field
    @property
    def effective_database_url(self) -> str:
        """Returns the appropriate database URL based on configuration.

        Priority:
        1. Lakebase with OAuth (if LAKEBASE_USE_OAUTH is True)
        2. Lakebase with password (if LAKEBASE_HOST and LAKEBASE_PASSWORD set)
        3. Legacy DATABASE_URL (for Neon or local dev)
        4. Default local PostgreSQL
        """
        # Lakebase with OAuth
        if self.LAKEBASE_USE_OAUTH and self.LAKEBASE_HOST and self.LAKEBASE_USER:
            from app.core.lakebase_auth import lakebase_auth
            if self.LAKEBASE_INSTANCE:
                lakebase_auth.configure(self.LAKEBASE_INSTANCE)
            return lakebase_auth.get_connection_string(
                host=self.LAKEBASE_HOST,
                database=self.LAKEBASE_DATABASE,
                user=self.LAKEBASE_USER,
                port=self.LAKEBASE_PORT
            )

        # Lakebase with static password
        if self.LAKEBASE_HOST and self.LAKEBASE_USER and self.LAKEBASE_PASSWORD:
            return (
                f"postgresql://{self.LAKEBASE_USER}:{self.LAKEBASE_PASSWORD}"
                f"@{self.LAKEBASE_HOST}:{self.LAKEBASE_PORT}"
                f"/{self.LAKEBASE_DATABASE}?sslmode=require"
            )

        # Legacy DATABASE_URL
        if self.DATABASE_URL:
            return self.DATABASE_URL

        return "postgresql://user:pass@localhost/dbname"

    @computed_field
    @property
    def is_using_lakebase(self) -> bool:
        """Check if Lakebase is configured."""
        return bool(self.LAKEBASE_HOST)

    # Security
    SECRET_KEY: str = "LrM0Shhrw0MhIzRtQhbUF30o4dTjE4d5m6PRDZhGUPM"  # Default matches Databricks secret
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS - Allow all origins since frontend/backend are same origin in production
    CORS_ORIGINS: List[str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []

    # Databricks - Set via environment variables (no hardcoded defaults)
    DATABRICKS_HOST: Optional[str] = None  # Required: set via DATABRICKS_HOST env var
    DATABRICKS_TOKEN: Optional[str] = None  # Required for local dev: set via DATABRICKS_TOKEN env var
    DATABRICKS_CLIENT_ID: Optional[str] = None  # Used by Databricks Apps for OAuth
    DATABRICKS_CLIENT_SECRET: Optional[str] = None  # Used by Databricks Apps for OAuth
    DATABRICKS_WAREHOUSE_PATH: Optional[str] = None  # SQL warehouse HTTP path

    # Email (optional)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()