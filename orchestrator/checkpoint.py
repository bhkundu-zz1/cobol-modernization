"""Writes job_run.tasks[i] checkpoints via MCP after every task (architecture.md section 3.3).

Real crash-resume mitigation this pass: after every task, its last action
before returning is this checkpoint write, so a crashed pipeline's progress
is durably recorded in CouchDB (not just Celery/Redis's ephemeral state).
The periodic-beat reconciler that automatically re-enqueues from the last
completed stage is explicitly NOT built this pass — see
docs/deferred_scope.md.
"""

from datetime import datetime, timezone

from fastmcp.exceptions import ToolError

from agents.common.mcp_client import MCPClient, get_mcp_client

_MAX_CONFLICT_RETRIES = 5


def _is_conflict(exc: ToolError) -> bool:
    return "conflict" in str(exc).lower()


def _read_job_run(client: MCPClient, project_id: str, job_run_id: str) -> dict | None:
    existing = client.couchdb_read(database="agent_runs", doc_id=f"{project_id}:{job_run_id}:job_run")
    docs = existing.get("docs", [])
    return docs[0] if docs else None


def write_checkpoint(
    *,
    project_id: str,
    job_run_id: str,
    agent_task_id: str,
    agent: str,
    status: str,
    error: dict | None = None,
    mcp_client: MCPClient | None = None,
) -> None:
    client = mcp_client or get_mcp_client()

    # The job_run doc is shared across every task in a job (and, for
    # epic/story generation, written both at task-start and task-end within
    # the same run) — read-modify-write here races against itself closely
    # enough in practice to hit CouchDB's optimistic-concurrency 409, so the
    # whole read-modify-write cycle retries on conflict rather than only
    # attempting it once.
    for attempt in range(_MAX_CONFLICT_RETRIES):
        job_run = _read_job_run(client, project_id, job_run_id)

        if job_run is None:
            job_run = {
                "_id": f"{project_id}:{job_run_id}:job_run",
                "type": "job_run",
                "job_run_id": job_run_id,
                "pipeline": "cobol_migration_analysis",
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": None,
                "tasks": [],
                "kill_requested": False,
            }

        tasks = job_run.get("tasks", [])
        existing_entry = next((t for t in tasks if t["agent_task_id"] == agent_task_id), None)
        if existing_entry is not None:
            existing_entry["status"] = status
        else:
            tasks.append({"agent_task_id": agent_task_id, "agent": agent, "status": status})
        job_run["tasks"] = tasks

        try:
            client.couchdb_write(
                database="agent_runs",
                doc=job_run,
                project_id=project_id,
                created_by=f"agent:{agent}",
                trace_id=f"{job_run_id}:{agent_task_id}",
            )
            break
        except ToolError as exc:
            if not _is_conflict(exc) or attempt == _MAX_CONFLICT_RETRIES - 1:
                raise

    # Same conflict-retry treatment as the job_run write above: this
    # standalone agent_task doc is keyed by agent_task_id, and a task that
    # calls write_checkpoint twice for the same agent_task_id (e.g. once at
    # start with status="running", again at completion/failure) writes to
    # the same doc twice — the second write must read the first's _rev
    # rather than constructing a revision-less doc that CouchDB rejects
    # with a 409 (confirmed as a live bug: a codegen failure's own
    # write_checkpoint(status="failed") call hit this exact 409, masking
    # the task's real underlying error).
    for attempt in range(_MAX_CONFLICT_RETRIES):
        existing_agent_task = client.couchdb_read(database="agent_runs", doc_id=f"{project_id}:{agent_task_id}:agent_task")
        existing_docs = existing_agent_task.get("docs", [])
        agent_task_doc = existing_docs[0] if existing_docs else {"_id": f"{project_id}:{agent_task_id}:agent_task"}
        agent_task_doc.update(
            {
                "type": "agent_task",
                "job_run_id": job_run_id,
                "agent": agent,
                "status": status,
                "error": error,
            }
        )
        try:
            client.couchdb_write(
                database="agent_runs",
                doc=agent_task_doc,
                project_id=project_id,
                created_by=f"agent:{agent}",
                trace_id=f"{job_run_id}:{agent_task_id}",
            )
            break
        except ToolError as exc:
            if not _is_conflict(exc) or attempt == _MAX_CONFLICT_RETRIES - 1:
                raise


def mark_job_run_finished(
    *, project_id: str, job_run_id: str, status: str, mcp_client: MCPClient | None = None
) -> None:
    client = mcp_client or get_mcp_client()

    for attempt in range(_MAX_CONFLICT_RETRIES):
        job_run = _read_job_run(client, project_id, job_run_id)
        if job_run is None:
            return
        job_run["status"] = status
        job_run["finished_at"] = datetime.now(timezone.utc).isoformat()
        try:
            client.couchdb_write(
                database="agent_runs",
                doc=job_run,
                project_id=project_id,
                created_by="system:orchestrator",
                trace_id=job_run_id,
            )
            return
        except ToolError as exc:
            if not _is_conflict(exc) or attempt == _MAX_CONFLICT_RETRIES - 1:
                raise
