"""Celery task: stage [2a] of the pipeline (architecture.md section 3.2).

Per-chunk (or whole-file) extraction, cross-chunk merge, self-check pass,
and confidence scoring, per
agents/skills/cobol-structural-analysis/SKILL.md.
"""

import json
import logging

from celery import shared_task

from agents.common import kill_switch
from agents.common.confidence import compute_structural_confidence
from agents.common.kill_switch import AgentKilled
from agents.common.langfuse_client import trace
from agents.common.llm_client import LLMClient, get_llm_client
from agents.common.mcp_client import MCPClient, get_mcp_client
from agents.common.skill_loader import load_skill
from orchestrator.checkpoint import write_checkpoint

from .merge import merge_chunk_extractions
from .prompts import build_extraction_prompt, build_self_check_prompt

logger = logging.getLogger("agents.cobol_structural")


def run_cobol_structural_analysis(
    *,
    project_id: str,
    job_run_id: str,
    agent_task_id: str,
    source_file_id: str,
    source_text: str,
    chunks: list[dict] | None = None,
    mcp_client: MCPClient | None = None,
    llm_client: LLMClient | None = None,
) -> dict:
    """Pure function version of the task body. `chunks` is the list of chunk
    docs (chunk_index/start_line/end_line/of_chunks) if the file was
    chunked; None/empty means the whole file is read directly."""
    mcp = mcp_client or get_mcp_client()
    llm = llm_client or get_llm_client()

    with trace(job_run_id, agent_task_id, name="cobol_structural"):
        kill_switch.check(project_id, job_run_id, client=mcp)

        skill = load_skill("cobol-structural-analysis")
        lines = source_text.splitlines()

        chunk_specs = chunks or [
            {"chunk_index": 0, "of_chunks": 1, "start_line": 1, "end_line": len(lines)}
        ]

        extractions = []
        for chunk in chunk_specs:
            chunk_text = "\n".join(lines[chunk["start_line"] - 1 : chunk["end_line"]])
            prompt = build_extraction_prompt(
                chunk_index=chunk["chunk_index"],
                of_chunks=chunk["of_chunks"],
                start_line=chunk["start_line"],
                end_line=chunk["end_line"],
                source_text=chunk_text,
            )
            extraction = llm.complete_json(skill.model, prompt, project_id=project_id, job_run_id=job_run_id)
            extractions.append(extraction)

        assembled = merge_chunk_extractions(extractions)

        self_check_prompt = build_self_check_prompt(
            assembled_structure_json=json.dumps(assembled), source_text=source_text
        )
        self_check = llm.complete_json(skill.model, self_check_prompt, project_id=project_id, job_run_id=job_run_id)

        unresolved_external_calls = [c for c in assembled["external_calls"] if not c.get("resolved", False)]
        confidence_score, needs_human_review = compute_structural_confidence(
            chunks_used=len(chunk_specs),
            discrepancies_found=self_check.get("discrepancies_found", 0),
            any_discrepancy_unresolved=not self_check.get("resolved", True),
            unresolved_external_call_count=len(unresolved_external_calls),
        )

        doc = {
            "type": "cobol_program_structure",
            "source_file_id": source_file_id,
            "program_id": assembled.get("program_id") or source_file_id,
            "divisions": assembled["divisions"],
            "copybooks_referenced": assembled["copybooks_referenced"],
            "paragraphs": assembled["paragraphs"],
            "call_graph": assembled["call_graph"],
            "external_calls": assembled["external_calls"],
            "extraction_method": "llm_native_chunked",
            "chunks_used": len(chunk_specs),
            "self_check_pass": {
                "performed": True,
                "discrepancies_found": self_check.get("discrepancies_found", 0),
                "resolved": self_check.get("resolved", False),
            },
            "confidence_score": confidence_score,
            "needs_human_review": needs_human_review,
        }

        write_result = mcp.couchdb_write(
            database="parsed_structure",
            doc=doc,
            project_id=project_id,
            created_by=f"agent:cobol-structural@v{skill.version}",
            trace_id=f"{job_run_id}:{agent_task_id}",
        )

        mcp.audit_append(
            project_id=project_id,
            event_category="agent_output",
            actor={"kind": "agent", "id": f"cobol-structural@v{skill.version}"},
            action="created_cobol_program_structure",
            subject_doc_id=write_result["id"],
            subject_doc_rev=write_result.get("rev"),
            model_used=skill.model,
            skill_version_hash=skill.content_hash,
        )

        kill_switch.check(project_id, job_run_id, client=mcp)

        write_checkpoint(
            project_id=project_id,
            job_run_id=job_run_id,
            agent_task_id=agent_task_id,
            agent="cobol_structural",
            status="completed",
            mcp_client=mcp,
        )

        return {
            "cobol_program_structure_id": write_result["id"],
            "confidence_score": confidence_score,
            "needs_human_review": needs_human_review,
        }


@shared_task(name="agents.cobol_structural.task.run_cobol_structural", queue="structural")
def run_cobol_structural(
    project_id: str,
    job_run_id: str,
    agent_task_id: str,
    source_file_id: str,
    source_text: str,
    chunks: list[dict] | None = None,
) -> dict:
    try:
        return run_cobol_structural_analysis(
            project_id=project_id,
            job_run_id=job_run_id,
            agent_task_id=agent_task_id,
            source_file_id=source_file_id,
            source_text=source_text,
            chunks=chunks,
        )
    except AgentKilled:
        # The pure function raised before reaching its own write_checkpoint
        # call — record the kill here so job_run doesn't stay stuck at
        # "running" forever (architecture.md section 7).
        kill_switch.record_kill(
            project_id=project_id, job_run_id=job_run_id, agent_task_id=agent_task_id, agent="cobol_structural"
        )
        raise
