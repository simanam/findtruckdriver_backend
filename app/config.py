"""
Configuration Management
Loads and validates environment variables using Pydantic Settings
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Uses .env file in development, environment variables in production.
    """

    # Application
    app_name: str = Field(default="Find a Truck Driver API", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    workers: int = Field(default=4, alias="WORKERS")

    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000",
        alias="CORS_ORIGINS"
    )

    @validator("cors_origins")
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Parse comma-separated CORS origins into list"""
        return [origin.strip() for origin in v.split(",")]

    # Supabase
    supabase_url: str = Field(..., alias="SUPABASE_URL")
    supabase_publishable_key: str = Field(..., alias="SUPABASE_PUBLISHABLE_KEY")
    supabase_service_key: str = Field(..., alias="SUPABASE_SERVICE_KEY")
    database_url: str = Field(..., alias="DATABASE_URL")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")

    # JWT
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=60,
        alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(
        default=30,
        alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # OTP
    otp_expiry_minutes: int = Field(default=10, alias="OTP_EXPIRY_MINUTES")
    otp_max_attempts: int = Field(default=3, alias="OTP_MAX_ATTEMPTS")

    # SMS Provider (Twilio - optional)
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_phone_number: str = Field(default="", alias="TWILIO_PHONE_NUMBER")

    # Location Settings
    location_update_interval_seconds: int = Field(
        default=60,
        alias="LOCATION_UPDATE_INTERVAL_SECONDS"
    )
    location_fuzz_rolling_miles: float = Field(
        default=2.0,
        alias="LOCATION_FUZZ_ROLLING_MILES"
    )
    location_fuzz_waiting_miles: float = Field(
        default=1.0,
        alias="LOCATION_FUZZ_WAITING_MILES"
    )
    location_fuzz_parked_miles: float = Field(
        default=0.5,
        alias="LOCATION_FUZZ_PARKED_MILES"
    )
    location_max_age_minutes: int = Field(
        default=30,
        alias="LOCATION_MAX_AGE_MINUTES"
    )

    # Geohash Settings
    geohash_precision_region: int = Field(default=2, alias="GEOHASH_PRECISION_REGION")
    geohash_precision_cluster: int = Field(default=4, alias="GEOHASH_PRECISION_CLUSTER")
    geohash_precision_metro: int = Field(default=6, alias="GEOHASH_PRECISION_METRO")
    geohash_precision_local: int = Field(default=8, alias="GEOHASH_PRECISION_LOCAL")

    # Hotspot Detection
    hotspot_min_waiting_drivers: int = Field(
        default=10,
        alias="HOTSPOT_MIN_WAITING_DRIVERS"
    )
    hotspot_radius_miles: float = Field(default=0.5, alias="HOTSPOT_RADIUS_MILES")
    hotspot_update_interval_minutes: int = Field(
        default=15,
        alias="HOTSPOT_UPDATE_INTERVAL_MINUTES"
    )

    # Caching
    stats_cache_ttl_seconds: int = Field(
        default=60,
        alias="STATS_CACHE_TTL_SECONDS"
    )
    cluster_cache_ttl_seconds: int = Field(
        default=60,
        alias="CLUSTER_CACHE_TTL_SECONDS"
    )
    facility_cache_ttl_seconds: int = Field(
        default=60,
        alias="FACILITY_CACHE_TTL_SECONDS"
    )

    # Rate Limiting
    rate_limit_otp_requests_per_hour: int = Field(
        default=5,
        alias="RATE_LIMIT_OTP_REQUESTS_PER_HOUR"
    )
    rate_limit_location_updates_per_minute: int = Field(
        default=2,
        alias="RATE_LIMIT_LOCATION_UPDATES_PER_MINUTE"
    )
    rate_limit_api_requests_per_minute: int = Field(
        default=100,
        alias="RATE_LIMIT_API_REQUESTS_PER_MINUTE"
    )

    # Monitoring
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    sentry_environment: str = Field(default="development", alias="SENTRY_ENVIRONMENT")
    sentry_traces_sample_rate: float = Field(
        default=0.1,
        alias="SENTRY_TRACES_SAMPLE_RATE"
    )

    # Background Jobs
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        alias="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/0",
        alias="CELERY_RESULT_BACKEND"
    )

    # Feature Flags
    feature_auto_status_detection: bool = Field(
        default=True,
        alias="FEATURE_AUTO_STATUS_DETECTION"
    )
    feature_hotspot_detection: bool = Field(
        default=True,
        alias="FEATURE_HOTSPOT_DETECTION"
    )
    feature_push_notifications: bool = Field(
        default=False,
        alias="FEATURE_PUSH_NOTIFICATIONS"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """
    Dependency function to get settings instance.
    Useful for dependency injection in FastAPI.
    """
    return settings
