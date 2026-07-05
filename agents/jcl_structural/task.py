"""Celery task: stage [2b] of the pipeline (architecture.md section 3.2) — STUB.

Real JCL structural extraction is deferred this pass (see
docs/deferred_scope.md). This task exists so the pipeline's chord fan-out
(architecture.md section 3.2) can include a JCL branch without blocking on
it: it marks itself skipped and writes no jcl_job_structure document.
"""

import logging

from celery import shared_task

from agents.common import kill_switch
from agents.common.langfuse_client import trace
from agents.common.mcp_client import MCPClient, get_mcp_client
from orchestrator.checkpoint import write_checkpoint

logger = logging.getLogger("agents.jcl_structural")


def run_jcl_structural_stub(
    *,
    project_id: str,
    job_run_id: str,
    agent_task_id: str,
    source_file_id: str,
    mcp_client: MCPClient | None = None,
) -> dict:
    mcp = mcp_client or get_mcp_client()

    with trace(job_run_id, agent_task_id, name="jcl_structural"):
        kill_switch.check(project_id, job_run_id, client=mcp)

        logger.info(
            "jcl_structural task is a stub this pass; marking skipped without writing jcl_job_structure",
            extra={"project_id": project_id, "job_run_id": job_run_id, "source_file_id": source_file_id},
        )

        write_checkpoint(
            project_id=project_id,
            job_run_id=job_run_id,
            agent_task_id=agent_task_id,
            agent="jcl_structural",
            status="skipped",
            mcp_client=mcp,
        )

        return {"source_file_id": source_file_id, "status": "skipped", "reason": "not_implemented_this_pass"}


@shared_task(name="agents.jcl_structural.task.run_jcl_structural", queue="structural")
def run_jcl_structural(project_id: str, job_run_id: str, agent_task_id: str, source_file_id: str) -> dict:
    return run_jcl_structural_stub(
        project_id=project_id, job_run_id=job_run_id, agent_task_id=agent_task_id, source_file_id=source_file_id
    )
