"""Chain/chord wiring for one upload batch (architecture.md section 3.2).

    source_upload
       |
       v
    [1] Ingestion & Chunking Agent  (Celery chain start)
       |
       +--> (fan-out per file, Celery group)
       v                              v
    [2a] COBOL Structural Agent   [2b] JCL Structural Agent (stub, always "skipped")
       |                              |
       +--------------+---------------+
                       v
            [3] Migration-Recommendation Agent  (chord callback)
                       |
                       v
            job_run marked "completed"

Epic/story (stage [4]) is NOT appended this pass — job_run completes once
stage [3] finishes for every subject, per the vertical-slice scope decision
that the review queue is the end of this pass's pipeline (docs/deferred_scope.md).
"""

import uuid

from celery import chain, chord, group

# Must be imported before any agents.*.task module below: @shared_task
# binds each task to whichever Celery app is "current" at import time, and
# without this import first, Celery falls back to its own bare default app
# (no broker/backend configured) instead of the properly-configured
# `harness` app — confirmed as a live bug where a signature built here
# carried a broker_url of None and apply_async() failed to connect.
import orchestrator.celery_app  # noqa: F401
from agents.cobol_structural.task import run_cobol_structural
from agents.ingestion_chunking.task import run_ingestion
from agents.jcl_structural.task import run_jcl_structural
from agents.recommendation.task import run_recommendation
from orchestrator.checkpoint import mark_job_run_finished, write_checkpoint


def new_job_run_id() -> str:
    return str(uuid.uuid4())


def new_agent_task_id() -> str:
    return str(uuid.uuid4())


def build_recommendation_group(project_id: str, job_run_id: str, cobol_structural_results: list[dict]):
    """One run_recommendation task per successfully-parsed COBOL program
    structure. Called from the chord callback once stage [2] completes for
    the whole batch. `cobol_structural_results` are run_cobol_structural's
    return values (each carrying a cobol_program_structure_id); run_recommendation
    reads the full structure document back out of CouchDB by that id."""
    tasks = []
    for result in cobol_structural_results:
        agent_task_id = new_agent_task_id()
        tasks.append(run_recommendation.s(result, project_id, job_run_id, agent_task_id))
    return group(tasks) if tasks else group([])


def build_structural_group(project_id: str, job_run_id: str, cobol_files: list[dict], jcl_files: list[dict]):
    """Stage [2]: one Celery group per file, COBOL branch real, JCL branch
    stub (architecture.md section 3.2). A chord tolerates an empty group,
    so a batch with no JCL files is fine."""
    cobol_tasks = [
        run_cobol_structural.s(
            project_id, job_run_id, new_agent_task_id(), f["source_file_id"], f["source_text"], f.get("chunks")
        )
        for f in cobol_files
    ]
    jcl_tasks = [
        run_jcl_structural.s(project_id, job_run_id, new_agent_task_id(), f["source_file_id"]) for f in jcl_files
    ]
    return group(cobol_tasks + jcl_tasks)


def build_pipeline(
    *,
    project_id: str,
    job_run_id: str,
    upload_batch_id: str,
    source_file_id: str,
    filename: str,
    source_text: str,
    source_origin: str,
    relative_path: str | None = None,
):
    """Builds the Celery chain for one uploaded/pulled file: ingestion ->
    cobol_structural -> recommendation. (This pass's vertical slice
    processes one primary COBOL file per pipeline run; the chord/group
    machinery above supports multi-file batches for when ingestion fans out
    more than one file, per architecture.md's batch design.)

    run_ingestion's return value is intentionally NOT piped into
    run_cobol_structural (it's called with an immutable signature, `.si()`)
    since run_cobol_structural needs source_text directly, not ingestion's
    metadata result — chaining still guarantees ordering (ingestion
    completes, including its secret-scan gate, before structural analysis
    starts). run_cobol_structural's result IS piped into run_recommendation
    (a mutable `.s()`), which reads the full parsed structure back out of
    CouchDB by the id in that result (see agents/recommendation/task.py).
    """
    ingestion_task_id = new_agent_task_id()
    structural_task_id = new_agent_task_id()
    recommendation_task_id = new_agent_task_id()

    return chain(
        run_ingestion.si(
            project_id, job_run_id, ingestion_task_id, upload_batch_id, source_file_id, filename, source_text, source_origin,
            relative_path,
        ),
        run_cobol_structural.si(project_id, job_run_id, structural_task_id, source_file_id, source_text, None),
        run_recommendation.s(project_id, job_run_id, recommendation_task_id),
    )
