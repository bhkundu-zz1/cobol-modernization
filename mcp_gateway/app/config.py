"""MCP gateway configuration — reads every value from the environment (.env), never hardcoded."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mcp_gateway_port: int = 7000

    couchdb_url: str = "http://localhost:5984"
    couchdb_user: str = "admin"
    couchdb_password: str = "changeme_local_dev_only"

    couchdb_db_sources: str = "sources"
    couchdb_db_parsed_structure: str = "parsed_structure"
    couchdb_db_agent_runs: str = "agent_runs"
    couchdb_db_recommendations: str = "recommendations"
    couchdb_db_backlog: str = "backlog"
    couchdb_db_audit_log: str = "audit_log"
    couchdb_db_config_meta: str = "config_meta"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db_kill_flags: int = 2

    mainframe_endevor_host: str = ""
    mainframe_endevor_credential_ref: str = "vault://mainframe/endevor/readonly"
    mainframe_panvalet_host: str = ""
    mainframe_panvalet_credential_ref: str = "vault://mainframe/panvalet/readonly"
    mainframe_changeman_host: str = ""
    mainframe_changeman_credential_ref: str = "vault://mainframe/changeman/readonly"

    # CODEGEN_GIT_TOKEN is resolved directly from os.environ inside
    # codegen_tools.py at call time (mirrors
    # agents/issue_tracker_export/adapter.py's credential handling) — never
    # stored on Settings, so it never appears in a request/response schema
    # or gets logged incidentally alongside the rest of this config object.
    codegen_git_repo_owner: str = ""
    codegen_git_repo_name: str = ""
    codegen_git_branch: str = "main"

    def known_databases(self) -> set[str]:
        return {
            self.couchdb_db_sources,
            self.couchdb_db_parsed_structure,
            self.couchdb_db_agent_runs,
            self.couchdb_db_recommendations,
            self.couchdb_db_backlog,
            self.couchdb_db_audit_log,
            self.couchdb_db_config_meta,
        }


settings = Settings()
