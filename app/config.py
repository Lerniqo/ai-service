from functools import lru_cache
import os
from typing import Optional
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

    # Service client configuration
    CONTENT_SERVICE_BASE_URL: Optional[str] = Field(default=None, env="CONTENT_SERVICE_BASE_URL")
    CONTENT_SERVICE_SECRET: Optional[str] = Field(default=None, env="CONTENT_SERVICE_SECRET")
    PROGRESS_SERVICE_BASE_URL: Optional[str] = Field(default=None, env="PROGRESS_SERVICE_BASE_URL")
    PROGRESS_SERVICE_SECRET: Optional[str] = Field(default=None, env="PROGRESS_SERVICE_SECRET")

    # Fallback for internal service communication when deployed in ECS
    @property
    def internal_progress_service_url(self) -> Optional[str]:
        """Get the internal progress service URL for ECS service discovery"""
        if self.PROGRESS_SERVICE_BASE_URL:
            return self.PROGRESS_SERVICE_BASE_URL
        # Fallback to service discovery URL when deployed in ECS
        # Check for ECS environment by looking for INTERNAL_ALB_DNS env var
        import os
        if self.is_production or os.getenv("INTERNAL_ALB_DNS"):
            return "http://progress-service.webapp-dev.local:3000"
        return None

    # Kafka configuration
    KAFKA_BOOTSTRAP_SERVERS: str = Field(default="localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    KAFKA_CLIENT_ID: str = Field(default="ai-service", env="KAFKA_CLIENT_ID")
    KAFKA_CONSUMER_GROUP_ID: str = Field(default="ai-service-events-consumer", env="KAFKA_CONSUMER_GROUP_ID")
    KAFKA_EVENTS_TOPIC: str = Field(default="events", env="KAFKA_EVENTS_TOPIC")

    # LLM configuration (Google Gemini)
    GOOGLE_API_KEY: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    LLM_MODEL: str = Field(default="gemini-1.5-flash", env="LLM_MODEL")
    LLM_TEMPERATURE: float = Field(default=0.7, env="LLM_TEMPERATURE")
    LLM_MAX_TOKENS: int = Field(default=2000, env="LLM_MAX_TOKENS")
    
    # Embedding configuration (Google)
    EMBEDDING_MODEL: str = Field(default="models/embedding-001", env="EMBEDDING_MODEL")
    EMBEDDING_CHUNK_SIZE: int = Field(default=1000, env="EMBEDDING_CHUNK_SIZE")
    EMBEDDING_CHUNK_OVERLAP: int = Field(default=200, env="EMBEDDING_CHUNK_OVERLAP")
    
    # Vector store configuration
    VECTOR_STORE_TYPE: str = Field(default="chroma", env="VECTOR_STORE_TYPE")  # chroma or faiss
    VECTOR_STORE_PATH: str = Field(default="./data/vector_store", env="VECTOR_STORE_PATH")
    VECTOR_STORE_COLLECTION: str = Field(default="learning_content", env="VECTOR_STORE_COLLECTION")
    
    # RAG configuration
    RAG_TOP_K: int = Field(default=5, env="RAG_TOP_K")
    RAG_SCORE_THRESHOLD: float = Field(default=0.7, env="RAG_SCORE_THRESHOLD")

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