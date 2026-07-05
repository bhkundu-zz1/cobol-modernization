"""Job/Pipeline Control Service configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    job_pipeline_control_service_port: int = 8005
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db_kill_flags: int = 2


settings = Settings()
