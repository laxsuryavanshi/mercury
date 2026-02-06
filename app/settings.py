from enum import StrEnum

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    STAGING = "staging"


class LogLevel(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CORSSettings(BaseModel):
    allow_origins: list[str] = Field(
        default=[], description="List of allowed origins for CORS"
    )
    allow_methods: list[str] = Field(
        default=[], description="List of allowed HTTP methods for CORS"
    )
    allow_headers: list[str] = Field(
        default=[], description="List of allowed headers for CORS"
    )
    allow_credentials: bool = Field(
        default=False, description="Allow credentials for CORS"
    )
    expose_headers: list[str] = Field(
        default=[], description="List of headers to expose for CORS"
    )
    max_age: int = Field(
        default=600, description="Max age for CORS preflight requests in seconds"
    )


class TrustedHostSettings(BaseModel):
    allowed_hosts: list[str] = Field(
        default=["*"], description="List of allowed hosts for TrustedHostMiddleware"
    )


class LoggingSettings(BaseModel):
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Minimum log level")
    log_json_format: bool = Field(
        default=False, description="Enable JSON formatted logs"
    )


class Settings(BaseSettings):
    # Application metadata
    app_name: str = Field(default="mercury", description="Application name")
    app_description: str = Field(
        default="A heavy, silvery liquid metal, toxic yet useful.",
        description="Application description",
    )
    app_version: str = Field(default="0.0.1.dev1", description="Application version")
    environment: Environment = Field(
        default=Environment.PRODUCTION, description="Application environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # CORS configuration
    cors: CORSSettings = Field(
        default_factory=CORSSettings, description="CORS configuration settings"
    )

    # Trusted host configuration
    trusted_host: TrustedHostSettings = Field(
        default_factory=TrustedHostSettings,
        description="Trusted host configuration settings",
    )

    # Logging configuration
    logging: LoggingSettings = Field(
        default_factory=LoggingSettings, description="Logging configuration settings"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        frozen=True,
        extra="ignore",
        env_nested_delimiter="__",
    )


settings = Settings()
