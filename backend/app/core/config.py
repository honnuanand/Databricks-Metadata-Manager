from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Databricks Metadata Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database  
    DATABASE_URL: str = "postgresql://user:pass@localhost/dbname"
    REDIS_URL: str = "redis://localhost:6379/0"
    
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