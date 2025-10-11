"""Application configuration and settings."""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings."""
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # API Configuration
    api_title: str = "Context Relay API"
    api_description: str = "Context Relay System Mock API for Frontend Development"
    api_version: str = "0.1.0"
    debug: bool = False

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # Database Configuration
    mongodb_uri: Optional[str] = None
    mongodb_db_name: Optional[str] = None

    # External API Keys
    voyage_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Environment
    environment: str = "development"

    # CORS Configuration
    cors_origins: list[str] = [
        "http://localhost:3000",  # React development server
        "http://localhost:8080",  # Vue development server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080"
    ]

    # Mock Data Configuration
    enable_mock_data: bool = True
    mock_data_seed: Optional[int] = None

    # Event Streaming Configuration
    sse_ping_interval: int = 30  # seconds
    sse_timeout: int = 300       # seconds
    event_history_size: int = 1000
    event_throttle_threshold: int = 10  # events per second per type

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Frontend Integration
    generate_typescript_types: bool = True
    typescript_output_file: str = "frontend-types.ts"

    # Testing Configuration
    test_mode: bool = False
    bdd_test_data_dir: str = "tests/fixtures"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()