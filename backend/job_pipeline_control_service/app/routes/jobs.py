"""POST /jobs, GET /jobs/{id}, POST /jobs/generate-epics-stories,
POST /jobs/generate-code — job_run lifecycle tracking (architecture.md
section 3.3).

POST /jobs triggers the Celery pipeline (orchestrator.pipeline.build_pipeline)
for an already-ingested source file and returns 202 + job_run_id
immediately — the multi-minute LLM pipeline is never in this request's
response path (architecture.md section 9.1).

POST /jobs/generate-epics-stories triggers agents.epic_story_writer.task
directly (no chain/chord — a single project-scoped task, not a per-file
pipeline) since epic/story generation clusters across every recommendation
for a project, not just one uploaded file — it cannot be appended to
build_pipeline's per-file chain.

POST /jobs/generate-code triggers agents.codegen.task directly, same
shape as generate-epics-stories — a single story-scoped task, not part of
the per-file pipeline chain, since code generation happens on demand
against one already-approved story, not automatically per upload.
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from agents.codegen.task import run_codegen_task
from agents.common.mcp_client import get_mcp_client
from agents.epic_story_writer.task import run_epic_story
from orchestrator.pipeline import build_pipeline, new_agent_task_id, new_job_run_id

router = APIRouter()


class TriggerJobRequest(BaseModel):
    project_id: str
    upload_batch_id: str
    source_file_id: str
    filename: str
    source_text: str
    source_origin: str = "manual_upload"
    relative_path: str | None = None


class GenerateEpicsStoriesRequest(BaseModel):
    project_id: str


class GenerateCodeRequest(BaseModel):
    project_id: str
    story_id: str
    target_language: Literal["python", "java_spring_boot"]


@router.post("/jobs", status_code=202)
def trigger_job(request: TriggerJobRequest, response: Response) -> dict:
    job_run_id = new_job_run_id()

    pipeline = build_pipeline(
        project_id=request.project_id,
        job_run_id=job_run_id,
        upload_batch_id=request.upload_batch_id,
        source_file_id=request.source_file_id,
        filename=request.filename,
        source_text=request.source_text,
        source_origin=request.source_origin,
        relative_path=request.relative_path,
    )
    pipeline.apply_async()

    response.status_code = 202
    return {"job_run_id": job_run_id, "status": "running"}


@router.post("/jobs/generate-epics-stories", status_code=202)
def trigger_epic_story_generation(request: GenerateEpicsStoriesRequest, response: Response) -> dict:
    job_run_id = new_job_run_id()
    agent_task_id = new_agent_task_id()

    run_epic_story.delay(request.project_id, job_run_id, agent_task_id)

    response.status_code = 202
    return {"job_run_id": job_run_id, "status": "running"}


@router.post("/jobs/generate-code", status_code=202)
def trigger_codegen(request: GenerateCodeRequest, response: Response) -> dict:
    job_run_id = new_job_run_id()
    agent_task_id = new_agent_task_id()

    run_codegen_task.delay(request.project_id, job_run_id, agent_task_id, request.story_id, request.target_language)

    response.status_code = 202
    return {"job_run_id": job_run_id, "status": "running"}


@router.get("/jobs/{job_run_id}")
def get_job(job_run_id: str, project_id: str) -> dict:
    mcp = get_mcp_client()
    result = mcp.couchdb_read(database="agent_runs", doc_id=f"{project_id}:{job_run_id}:job_run")
    docs = result.get("docs", [])
    if not docs:
        raise HTTPException(status_code=404, detail="job_run not found")
    return docs[0]
