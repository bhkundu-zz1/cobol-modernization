"""Review BFF configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    review_bff_port: int = 8002
    recommendation_service_url: str = "http://localhost:8006"
    job_pipeline_control_service_url: str = "http://localhost:8005"
    source_mgmt_service_url: str = "http://localhost:8004"
    epic_story_service_url: str = "http://localhost:8007"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db_cache: int = 1
    cache_ttl_seconds: int = 15


settings = Settings()
