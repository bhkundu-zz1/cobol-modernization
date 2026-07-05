"""Pipeline execution tracking document models (architecture.md section 2.2).

JobRun mirrors Celery task state durably in CouchDB — Celery's own result
backend is ephemeral/opaque, and compliance needs a durable, queryable
record (architecture.md section 3.1).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from .envelope import DocEnvelope

AgentTaskStatus = Literal["pending", "running", "completed", "failed", "skipped", "killed"]


class AgentTaskEntry(BaseModel):
    """One entry in JobRun.tasks — a lightweight checkpoint record, not the
    full AgentTask document (which lives separately in `agent_runs`)."""

    agent_task_id: str
    agent: str
    status: AgentTaskStatus


class JobRun(DocEnvelope):
    type: Literal["job_run"] = "job_run"
    job_run_id: str
    pipeline: Literal["cobol_migration_analysis"] = "cobol_migration_analysis"
    status: Literal["running", "completed", "failed", "killed"]
    started_at: datetime
    finished_at: datetime | None = None
    tasks: list[AgentTaskEntry] = []
    kill_requested: bool = False
    kill_requested_by: str | None = None
    kill_requested_at: datetime | None = None


class AgentTask(DocEnvelope):
    type: Literal["agent_task"] = "agent_task"
    job_run_id: str
    agent: str
    status: AgentTaskStatus
    skill_version_hash: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: dict | None = None
