"""Ingestion BFF configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ingestion_bff_port: int = 8001
    source_mgmt_service_url: str = "http://localhost:8004"
    job_pipeline_control_service_url: str = "http://localhost:8005"


settings = Settings()
