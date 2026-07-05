"""Celery task: stage [1] of the pipeline (architecture.md section 3.2).

Secret-scan, classify, chunk (if needed), and write source_file/chunk docs
via MCP. Runs identically for manual-upload and mainframe-pull sources —
both produce the same source_file shape (source_origin distinguishes them).
"""

import logging

from celery import shared_task

from agents.common import kill_switch
from agents.common.kill_switch import AgentKilled
from agents.common.langfuse_client import trace
from agents.common.mcp_client import MCPClient, get_mcp_client
from agents.common.skill_loader import load_skill
from orchestrator.checkpoint import write_checkpoint

from .chunker import build_chunks, chunking_required, classify_language
from .secret_scan import build_secret_scan_result

logger = logging.getLogger("agents.ingestion_chunking")


def run_ingestion_chunking(
    *,
    project_id: str,
    job_run_id: str,
    agent_task_id: str,
    upload_batch_id: str,
    source_file_id: str,
    filename: str,
    source_text: str,
    source_origin: str,
    relative_path: str | None = None,
    mcp_client: MCPClient | None = None,
) -> dict:
    """Pure function version of the task body, for direct unit testing
    without a Celery worker. `run_ingestion` (the @shared_task below) is a
    thin wrapper around this."""
    client = mcp_client or get_mcp_client()

    with trace(job_run_id, agent_task_id, name="ingestion_chunking"):
        kill_switch.check(project_id, job_run_id, client=client)

        skill = load_skill("ingestion-chunking")

        secret_scan_result = build_secret_scan_result({filename: source_text})

        language = classify_language(filename, source_text)
        line_count = len(source_text.splitlines())
        needs_chunking = chunking_required(line_count)

        client.couchdb_write(
            database="sources",
            doc={
                "_id": f"{project_id}:{source_file_id}:source_file",
                "type": "source_file",
                "source_file_id": source_file_id,
                "upload_batch_id": upload_batch_id,
                "filename": filename,
                "language": language,
                "line_count": line_count,
                "chunking_required": needs_chunking,
                "source_origin": source_origin,
                "source_text": source_text,
                "relative_path": relative_path,
            },
            project_id=project_id,
            created_by=f"agent:ingestion-chunking@v{skill.version}",
            trace_id=f"{job_run_id}:{agent_task_id}",
        )

        chunk_docs = []
        if needs_chunking:
            for chunk in build_chunks(source_text):
                result = client.couchdb_write(
                    database="sources",
                    doc={
                        "type": "chunk",
                        "source_file_id": source_file_id,
                        **chunk,
                    },
                    project_id=project_id,
                    created_by=f"agent:ingestion-chunking@v{skill.version}",
                    trace_id=f"{job_run_id}:{agent_task_id}",
                )
                chunk_docs.append(result)

        kill_switch.check(project_id, job_run_id, client=client)

        write_checkpoint(
            project_id=project_id,
            job_run_id=job_run_id,
            agent_task_id=agent_task_id,
            agent="ingestion_chunking",
            status="completed",
            mcp_client=client,
        )

        return {
            "source_file_id": source_file_id,
            "language": language,
            "chunking_required": needs_chunking,
            "chunks_written": len(chunk_docs),
            "secret_scan_result": secret_scan_result,
            "skill_version_hash": skill.content_hash,
        }


@shared_task(name="agents.ingestion_chunking.task.run_ingestion", queue="ingestion")
def run_ingestion(
    project_id: str,
    job_run_id: str,
    agent_task_id: str,
    upload_batch_id: str,
    source_file_id: str,
    filename: str,
    source_text: str,
    source_origin: str,
    relative_path: str | None = None,
) -> dict:
    try:
        return run_ingestion_chunking(
            project_id=project_id,
            job_run_id=job_run_id,
            agent_task_id=agent_task_id,
            upload_batch_id=upload_batch_id,
            source_file_id=source_file_id,
            filename=filename,
            source_text=source_text,
            source_origin=source_origin,
            relative_path=relative_path,
        )
    except AgentKilled:
        kill_switch.record_kill(
            project_id=project_id, job_run_id=job_run_id, agent_task_id=agent_task_id, agent="ingestion_chunking"
        )
        raise
