"""Editor/Admin BFF configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    editor_admin_bff_port: int = 8003
    epic_story_service_url: str = "http://localhost:8007"


settings = Settings()
