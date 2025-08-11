from functools import lru_cache
import os
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Determine current environment (default: development)
_ENV = os.getenv("ENV", "development").lower()
# Load the corresponding .env file (e.g., .env.development, .env.testing, .env.production)
load_dotenv(f".env.{_ENV}", override=True)

class Settings(BaseSettings):
    """Application settings configuration loaded from environment variables.

    The active environment is selected via the ENV variable (development|testing|production).
    Values are loaded from the matching .env.<environment> file if present.
    """
    ENV: str = Field(default=_ENV)

    APP_NAME: str = Field(default="MyApp", env="APP_NAME")
    APP_VERSION: str = Field(default="1.0.0", env="APP_VERSION")
    APP_DESCRIPTION: str = Field(default="This is my app", env="APP_DESCRIPTION")

    HOST: str = Field(default="127.0.0.1", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    RELOAD: bool = Field(default=False, env="RELOAD")  # Typically True only in development .env

    @property
    def is_development(self) -> bool:
        return self.ENV == "development"

    @property
    def is_testing(self) -> bool:
        return self.ENV == "testing"

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

@lru_cache()
def get_settings() -> Settings:
    """Get the cached application settings instance."""
    return Settings()