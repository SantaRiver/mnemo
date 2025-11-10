"""Application settings using pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = Field(default="nlp-service")
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # LLM Configuration
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4-turbo-preview")
    openai_max_tokens: int = Field(default=2000)
    openai_temperature: float = Field(default=0.3)
    llm_timeout_seconds: int = Field(default=10)
    llm_max_retries: int = Field(default=2)

    # Cache Configuration
    redis_url: str = Field(default="redis://localhost:6379/0")
    cache_ttl_seconds: int = Field(default=604800)  # 7 days
    cache_enabled: bool = Field(default=True)

    # Database Configuration
    database_url: str = Field(default="sqlite:///./nlp_service.db")

    # Heuristics Configuration
    heuristic_confidence_threshold: float = Field(default=0.8)
    use_llm_fallback: bool = Field(default=True)

    # Time Estimation Defaults
    default_time_minutes: int = Field(default=10)
    achievement_default_weight: int = Field(default=10)

    # Rate Limiting
    llm_rate_limit_per_minute: int = Field(default=60)
    llm_rate_limit_per_hour: int = Field(default=1000)

    # Monitoring
    prometheus_port: int = Field(default=9090)
    metrics_enabled: bool = Field(default=True)

    # Security
    pii_redaction_enabled: bool = Field(default=True)


def get_settings() -> Settings:
    """Get settings instance."""
    return Settings()
