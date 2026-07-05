"""Celery task: stage [3] of the pipeline (architecture.md section 3.2).

Reasons over a parsed cobol_program_structure to recommend a migration
target, per agents/skills/migration-recommendation/SKILL.md. Guardrail
output-schema validation (rationale/alternative_considered/risk_flags
required) is enforced via guardrails_client.check_output before the
document is written.
"""

import json
import logging

from celery import shared_task
from pydantic import BaseModel

from agents.common import kill_switch
from agents.common.confidence import cap_recommendation_confidence
from agents.common.guardrails_client import check_output
from agents.common.kill_switch import AgentKilled
from agents.common.langfuse_client import trace
from agents.common.llm_client import LLMClient, get_llm_client
from agents.common.mcp_client import MCPClient, get_mcp_client
from agents.common.skill_loader import load_skill
from orchestrator.checkpoint import mark_job_run_finished, write_checkpoint

from .decision_factors import build_decision_factors

logger = logging.getLogger("agents.recommendation")

RECOMMENDATION_PROMPT_TEMPLATE = """You are recommending a migration target for a COBOL program being
modernized off the mainframe. You are given its extracted structure and a
set of decision factors. Recommend exactly one target from this set:
java_spring_boot, python_microservice, python_airflow_dag, python_cron_script.

You MUST provide:
1. "rationale": a clear explanation grounded in the decision factors below.
2. "alternative_considered": the next-best target and a specific reason it
   was not chosen.
3. "risk_flags": a list of specific concerns visible in the structure.

STRUCTURE:
---
{structure_json}
---

DECISION FACTORS:
---
{decision_factors_json}
---

Return JSON:
{{
  "recommended_target": "...",
  "rationale": "...",
  "confidence_score": <float 0-1>,
  "alternative_considered": {{"target": "...", "why_rejected": "..."}},
  "risk_flags": ["..."]
}}"""


class RecommendationLLMOutput(BaseModel):
    """The shape guardrails_client.check_output validates against — not the
    full MigrationRecommendation envelope (project_id/trace_id/etc. are
    added after validation), just the LLM's own required output fields."""

    recommended_target: str
    rationale: str
    confidence_score: float
    alternative_considered: dict
    risk_flags: list[str]


def run_migration_recommendation(
    *,
    project_id: str,
    job_run_id: str,
    agent_task_id: str,
    cobol_program_structure: dict,
    mcp_client: MCPClient | None = None,
    llm_client: LLMClient | None = None,
) -> dict:
    mcp = mcp_client or get_mcp_client()
    llm = llm_client or get_llm_client()

    with trace(job_run_id, agent_task_id, name="recommendation"):
        kill_switch.check(project_id, job_run_id, client=mcp)

        skill = load_skill("migration-recommendation")
        decision_factors = build_decision_factors(cobol_program_structure)

        prompt = RECOMMENDATION_PROMPT_TEMPLATE.format(
            structure_json=json.dumps(cobol_program_structure), decision_factors_json=json.dumps(decision_factors)
        )

        def call_llm() -> dict:
            return llm.complete_json(skill.model, prompt, project_id=project_id, job_run_id=job_run_id)

        raw_output = call_llm()
        validated = check_output(
            raw_output,
            RecommendationLLMOutput,
            project_id=project_id,
            job_run_id=job_run_id,
            retry_fn=call_llm,
            max_retries=1,
        )

        capped_confidence = cap_recommendation_confidence(
            validated.confidence_score, cobol_program_structure.get("confidence_score", 1.0)
        )

        risk_flags = list(validated.risk_flags)
        if cobol_program_structure.get("needs_human_review"):
            risk_flags.append(
                "underlying structural extraction flagged for human review"
            )

        # subject_id (the cobol_program_structure doc id, e.g.
        # "acme-2026:<uuid>:cobol_program_structure") is meaningless to a
        # reviewer — denormalize the actual uploaded filename here, at
        # write time, so the review queue can display something a human
        # recognizes without a second lookup on every render.
        source_filename = None
        source_file_id = cobol_program_structure.get("source_file_id")
        if source_file_id:
            source_file_result = mcp.couchdb_read(
                database="sources", doc_id=f"{project_id}:{source_file_id}:source_file"
            )
            source_file_docs = source_file_result.get("docs", [])
            if source_file_docs:
                source_filename = source_file_docs[0].get("filename")

        doc = {
            "type": "migration_recommendation",
            "subject_type": "cobol_program",
            "subject_id": cobol_program_structure.get("_id") or cobol_program_structure.get("source_file_id"),
            "subject_filename": source_filename,
            "source_file_id": source_file_id,
            "program_id": cobol_program_structure.get("program_id"),
            "job_run_id": job_run_id,
            "recommended_target": validated.recommended_target,
            "rationale": validated.rationale,
            "confidence_score": capped_confidence,
            "decision_factors": decision_factors,
            "alternative_considered": validated.alternative_considered,
            "risk_flags": risk_flags,
            "produced_by_agent": f"recommendation-agent@v{skill.version}",
            "produced_by_model": skill.model,
            "human_review_status": "pending",
        }

        write_result = mcp.couchdb_write(
            database="recommendations",
            doc=doc,
            project_id=project_id,
            created_by=f"agent:recommendation@v{skill.version}",
            trace_id=f"{job_run_id}:{agent_task_id}",
        )

        mcp.audit_append(
            project_id=project_id,
            event_category="agent_output",
            actor={"kind": "agent", "id": f"recommendation@v{skill.version}"},
            action="created_recommendation",
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
            agent="recommendation",
            status="completed",
            mcp_client=mcp,
        )
        # Recommendation is the last stage in this pass's pipeline (epic/story
        # is not appended — see orchestrator/pipeline.py) — job_run is marked
        # completed here.
        mark_job_run_finished(project_id=project_id, job_run_id=job_run_id, status="completed", mcp_client=mcp)

        return {"migration_recommendation_id": write_result["id"], "recommended_target": validated.recommended_target}


@shared_task(name="agents.recommendation.task.run_recommendation", queue="recommendation")
def run_recommendation(
    cobol_structural_result: dict,
    project_id: str,
    job_run_id: str,
    agent_task_id: str,
) -> dict:
    """`cobol_structural_result` is run_cobol_structural's return value
    (piped in automatically by the Celery chain in orchestrator/pipeline.py)
    — this task reads the full cobol_program_structure document by the id
    it contains, rather than requiring the whole structure to be passed
    through Celery's result backend."""
    mcp = get_mcp_client()
    read_result = mcp.couchdb_read(
        database="parsed_structure", doc_id=cobol_structural_result["cobol_program_structure_id"]
    )
    docs = read_result.get("docs", [])
    if not docs:
        raise ValueError(
            f"cobol_program_structure {cobol_structural_result['cobol_program_structure_id']!r} not found"
        )

    try:
        return run_migration_recommendation(
            project_id=project_id,
            job_run_id=job_run_id,
            agent_task_id=agent_task_id,
            cobol_program_structure=docs[0],
        )
    except AgentKilled:
        kill_switch.record_kill(
            project_id=project_id, job_run_id=job_run_id, agent_task_id=agent_task_id, agent="recommendation"
        )
        raise
