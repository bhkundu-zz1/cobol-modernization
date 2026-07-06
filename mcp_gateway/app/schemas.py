"""Pydantic request/response models for each MCP tool (per agents/tools/*.md declarations)."""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

# --- couchdb.read / couchdb.write -------------------------------------------------


class CouchDBReadRequest(BaseModel):
    database: str
    doc_id: str | None = None
    mango_selector: dict[str, Any] | None = None
    limit: int = 50


class CouchDBReadResult(BaseModel):
    docs: list[dict[str, Any]]
    bookmark: str | None = None


class CouchDBWriteRequest(BaseModel):
    database: str
    doc: dict[str, Any]
    project_id: str
    created_by: str
    trace_id: str


class CouchDBWriteResult(BaseModel):
    id: str
    rev: str


# --- audit.append / audit.export_range --------------------------------------------

AuditEventCategory = Literal[
    "agent_output",
    "human_review_decision",
    "guardrail_decision",
    "export",
    "kill_switch",
    "config_change",
]


class AuditActor(BaseModel):
    kind: Literal["agent", "user", "system"]
    id: str


class AuditAppendRequest(BaseModel):
    project_id: str
    event_category: AuditEventCategory
    actor: AuditActor
    action: str
    subject_doc_id: str
    subject_doc_rev: str | None = None
    before_state_hash: str | None = None
    after_state_hash: str | None = None
    model_used: str | None = None
    skill_version_hash: str | None = None

    model_config = {"protected_namespaces": ()}


class AuditAppendResult(BaseModel):
    id: str
    rev: str
    this_event_hash: str


class AuditExportRangeRequest(BaseModel):
    project_id: str
    start: datetime
    end: datetime


class AuditExportRangeResult(BaseModel):
    events: list[dict[str, Any]]
    chain_valid: bool


# --- kill.check / kill.set ---------------------------------------------------------


class KillCheckRequest(BaseModel):
    project_id: str
    job_run_id: str


class KillCheckResult(BaseModel):
    killed: bool
    reason: str | None = None


class KillSetRequest(BaseModel):
    scope: Literal["all", "project", "job_run"]
    scope_id: str | None = None
    requested_by: str


class KillSetResult(BaseModel):
    ok: bool


# --- mainframe.fetch_source ---------------------------------------------------------


class MainframeFetchSourceRequest(BaseModel):
    tool: Literal["endevor", "panvalet", "changeman", "mock"]
    host: str
    credential_ref: str
    system: str
    subsystem: str
    element_type: str
    element_id: str | None = None


class MainframeElementSummary(BaseModel):
    element_id: str
    element_type: str
    version: str | None = None


class MainframeListResult(BaseModel):
    elements: list[MainframeElementSummary]


class MainframePullResult(BaseModel):
    source_text: str
    metadata: dict[str, Any]


# --- issue_tracker.export -----------------------------------------------------


class IssueTrackerExportRequest(BaseModel):
    tool: Literal["github", "jira"]
    connection_config: dict[str, Any]
    epic_ids: list[str]
    story_ids: list[str]


class ExportedStoryResult(BaseModel):
    story_id: str
    external_issue_key: str
    external_issue_url: str


class FailedStoryResult(BaseModel):
    story_id: str
    reason: str


class ExportedMilestoneResult(BaseModel):
    epic_id: str
    external_milestone_id: str
    external_milestone_url: str


class IssueTrackerExportResult(BaseModel):
    exported: list[ExportedStoryResult]
    failed: list[FailedStoryResult]
    epic_milestones: list[ExportedMilestoneResult]


# --- codegen.commit_files -------------------------------------------------------


class CodegenFileEntry(BaseModel):
    relative_path: str
    content: str


class CodegenCommitFilesRequest(BaseModel):
    project_id: str
    story_id: str
    files: list[CodegenFileEntry]
    commit_message: str
    requesting_agent: str


class CodegenCommitFilesResult(BaseModel):
    commit_sha: str
    commit_url: str
    repo_path: str


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
