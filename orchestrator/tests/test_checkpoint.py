"""Regression test: write_checkpoint/mark_job_run_finished do a
read-modify-write against the shared job_run doc. Two writes to that same
doc close together (e.g. epic_story_writer's own start-of-task and
end-of-task checkpoints) can race closely enough to hit CouchDB's
optimistic-concurrency 409 in practice — confirmed live against a real
run. Both functions must retry the whole read-modify-write cycle on
conflict instead of raising on the first attempt, or a real 409 leaves
job_run.status stuck at "running" forever."""

from typing import Any

import pytest
from fastmcp.exceptions import ToolError

from orchestrator.checkpoint import mark_job_run_finished, write_checkpoint

PROJECT_ID = "acme-2026"
JOB_RUN_ID = "jr-1"


class ConflictOnceThenSucceedClient:
    """Fakes a CouchDB doc store where the first couchdb_write for a given
    doc_id after doc creation raises a 409 conflict, then subsequent writes
    succeed — simulating a concurrent writer that won the race."""

    def __init__(self, conflicts_before_success: int) -> None:
        self.docs: dict[str, dict[str, Any]] = {}
        self._remaining_conflicts = conflicts_before_success
        self.write_attempts = 0

    def couchdb_read(self, database: str, doc_id: str | None = None, **_: Any) -> dict:
        doc = self.docs.get(doc_id)
        return {"docs": [doc] if doc else [], "bookmark": None}

    def couchdb_write(self, database: str, doc: dict, **_: Any) -> dict:
        self.write_attempts += 1
        if doc.get("type") == "job_run" and self._remaining_conflicts > 0:
            self._remaining_conflicts -= 1
            raise ToolError("Error calling tool 'couchdb_write': Error: conflict: Document update conflict., Status code: 409")
        self.docs[doc["_id"]] = dict(doc)
        return {"id": doc["_id"], "rev": "2-fake"}


def test_write_checkpoint_retries_through_a_single_conflict():
    client = ConflictOnceThenSucceedClient(conflicts_before_success=1)

    write_checkpoint(
        project_id=PROJECT_ID,
        job_run_id=JOB_RUN_ID,
        agent_task_id="task-1",
        agent="epic_story_writer",
        status="running",
        mcp_client=client,
    )

    job_run = client.docs[f"{PROJECT_ID}:{JOB_RUN_ID}:job_run"]
    assert job_run["tasks"][0]["status"] == "running"


def test_write_checkpoint_reraises_after_exhausting_retries():
    client = ConflictOnceThenSucceedClient(conflicts_before_success=999)

    with pytest.raises(ToolError):
        write_checkpoint(
            project_id=PROJECT_ID,
            job_run_id=JOB_RUN_ID,
            agent_task_id="task-1",
            agent="epic_story_writer",
            status="running",
            mcp_client=client,
        )


def test_mark_job_run_finished_retries_through_a_single_conflict():
    client = ConflictOnceThenSucceedClient(conflicts_before_success=0)
    write_checkpoint(
        project_id=PROJECT_ID,
        job_run_id=JOB_RUN_ID,
        agent_task_id="task-1",
        agent="epic_story_writer",
        status="completed",
        mcp_client=client,
    )

    client._remaining_conflicts = 1
    mark_job_run_finished(project_id=PROJECT_ID, job_run_id=JOB_RUN_ID, status="completed", mcp_client=client)

    job_run = client.docs[f"{PROJECT_ID}:{JOB_RUN_ID}:job_run"]
    assert job_run["status"] == "completed"
    assert job_run["finished_at"] is not None
