"""
DevPilot AI Configuration Settings
"""
import os
from typing import List, Union, Set
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET_KEYS: Set[str] = {
    "devpilot-super-secret-key-change-in-production-0123456789abcdef",
    "devpilot-insecure-secret-key-change-in-production-0123456789abcdef",
    "devpilot-docker-secret-change-in-prod-0123456789",
    "secret",
    "changeme",
    "password",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    APP_NAME: str = "DevPilot AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_V1_STR: str = "/api"

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        env = (self.ENVIRONMENT or "").strip().lower()
        if env in {"production", "prod"}:
            if not self.SECRET_KEY or self.SECRET_KEY in INSECURE_SECRET_KEYS or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "Insecure or default SECRET_KEY detected in production environment! "
                    "A unique, cryptographically strong SECRET_KEY (minimum 32 characters) "
                    "must be provided via the SECRET_KEY environment variable."
                )
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError(
                    "SQLite database cannot be used in a production environment! "
                    "Please configure a valid PostgreSQL DATABASE_URL via environment variables."
                )
        return self

    # Security & Authentication
    SECRET_KEY: str = "devpilot-super-secret-key-change-in-production-0123456789abcdef"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = "sqlite:///./devpilot.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # GitHub Integration
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_APP_ID: str = ""
    GITHUB_PRIVATE_KEY_PATH: str = ""
    GITHUB_WEBHOOK_SECRET: str = ""

    # LLM Settings
    DEFAULT_LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL_NAME: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_NAME: str = "gemini-1.5-pro"
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Execution Sandbox
    DOCKER_SANDBOX_NETWORK_DISABLED: bool = True
    DOCKER_SANDBOX_CPU_LIMIT: float = 1.0
    DOCKER_SANDBOX_MEMORY_LIMIT: str = "512m"
    DOCKER_SANDBOX_TIMEOUT_SECONDS: int = 60
    SANDBOX_TEMP_DIR: str = "./execution/sandbox/workspaces"

    # Observability
    PROMETHEUS_METRICS_ENABLED: bool = True


settings = Settings()
