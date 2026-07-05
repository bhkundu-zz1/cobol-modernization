"""Source Management Service configuration — reads from .env, never hardcoded."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    source_mgmt_service_port: int = 8004
    default_project_id: str = "acme-2026"
    mainframe_endevor_host: str = ""
    mainframe_endevor_credential_ref: str = "vault://mainframe/endevor/readonly"
    mainframe_panvalet_host: str = ""
    mainframe_panvalet_credential_ref: str = "vault://mainframe/panvalet/readonly"
    mainframe_changeman_host: str = ""
    mainframe_changeman_credential_ref: str = "vault://mainframe/changeman/readonly"


settings = Settings()
