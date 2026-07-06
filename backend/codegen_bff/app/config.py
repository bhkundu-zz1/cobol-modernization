"""Codegen BFF configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    codegen_bff_port: int = 8008
    recommendation_service_url: str = "http://localhost:8006"
    epic_story_service_url: str = "http://localhost:8007"
    job_pipeline_control_service_url: str = "http://localhost:8005"


settings = Settings()
