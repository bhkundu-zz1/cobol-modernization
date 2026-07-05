"""Agent-side kill-switch check helper (architecture.md section 7).

Every Celery task calls kill_switch.check() before each unit of work: at
task start, before each LLM call, before each MCP tool call, and inside any
chunk-processing loop for long tasks.
"""

from .mcp_client import MCPClient, get_mcp_client


class AgentKilled(Exception):
    """Raised when kill_switch.check() finds the task has been killed. The
    caller must stop immediately without writing further recommendation/epic
    documents; partial output already written stays visible to reviewers."""

    def __init__(self, reason: str | None) -> None:
        self.reason = reason
        super().__init__(reason or "agent task killed")


def check(project_id: str, job_run_id: str, client: MCPClient | None = None) -> None:
    """Raises AgentKilled if the pipeline for this project/job_run has been
    killed. Returns None (no-op) otherwise."""
    client = client or get_mcp_client()
    result = client.kill_check(project_id=project_id, job_run_id=job_run_id)
    if result.get("killed"):
        raise AgentKilled(result.get("reason"))


def record_kill(
    *,
    project_id: str,
    job_run_id: str,
    agent_task_id: str,
    agent: str,
    client: MCPClient | None = None,
) -> None:
    """Called from an `except AgentKilled` handler in each real task: writes
    the agent_task checkpoint as "killed" and marks the whole job_run
    "killed" (architecture.md section 7 — the review UI must show
    job_run.status: killed and tag partial output as incomplete, not leave
    it stuck at "running" forever, which is what happened before this
    existed — confirmed as a live bug during the kill-switch drill: a task
    killed mid-flight raised AgentKilled before ever reaching its own
    write_checkpoint call, so no record of the kill ever reached CouchDB).
    """
    # Imported here, not at module level, to avoid a circular import
    # (orchestrator.checkpoint -> agents.common.mcp_client, and this module
    # already lives in agents.common).
    from orchestrator.checkpoint import mark_job_run_finished, write_checkpoint  # noqa: PLC0415

    write_checkpoint(
        project_id=project_id,
        job_run_id=job_run_id,
        agent_task_id=agent_task_id,
        agent=agent,
        status="killed",
        mcp_client=client,
    )
    mark_job_run_finished(project_id=project_id, job_run_id=job_run_id, status="killed", mcp_client=client)
