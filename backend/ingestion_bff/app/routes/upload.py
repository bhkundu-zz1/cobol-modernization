"""POST /bff/uploads, POST /bff/mainframe-pulls — fans out to source-mgmt-service
and job-pipeline-control-service (architecture.md sections 1a, 8, 9.1).

Returns 202 + job_run_id immediately; the multi-minute LLM pipeline runs
async after this request completes (architecture.md section 9.1's <5s NFR
budget covers this request, not the pipeline itself).
"""

from typing import Literal

import httpx
from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/bff")


class MainframePullBFFRequest(BaseModel):
    project_id: str
    tool: Literal["endevor", "panvalet", "changeman", "mock"]
    system: str
    subsystem: str
    element_type: str = "COBOL"
    element_id: str


async def _trigger_job(
    client: httpx.AsyncClient,
    *,
    project_id,
    upload_batch_id,
    source_file_id,
    filename,
    source_text,
    source_origin,
    relative_path: str | None = None,
) -> dict:
    response = await client.post(
        f"{settings.job_pipeline_control_service_url}/jobs",
        json={
            "project_id": project_id,
            "upload_batch_id": upload_batch_id,
            "source_file_id": source_file_id,
            "filename": filename,
            "source_text": source_text,
            "source_origin": source_origin,
            "relative_path": relative_path,
        },
    )
    response.raise_for_status()
    return response.json()


@router.post("/uploads", status_code=202)
async def create_upload(
    response: Response,
    project_id: str = Form(...),
    files: list[UploadFile] = File(...),
    relative_paths: list[str] | None = Form(None),
) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="at least one file is required")

    file_bytes = [(f.filename, await f.read()) for f in files]

    async with httpx.AsyncClient(timeout=30.0) as client:
        data = {"project_id": project_id}
        if relative_paths:
            data["relative_paths"] = relative_paths
        upload_response = await client.post(
            f"{settings.source_mgmt_service_url}/uploads",
            data=data,
            files=[("files", (name, content, "text/plain")) for name, content in file_bytes],
        )
        upload_response.raise_for_status()
        upload_result = upload_response.json()

        # One pipeline job per uploaded file — a folder selection with
        # multiple COBOL programs must produce a recommendation for every
        # program, not just the first (build_pipeline's own docstring
        # already anticipates multi-file batches; this was previously
        # truncated to files[0] only, a real gap, not by design).
        jobs = [
            await _trigger_job(
                client,
                project_id=project_id,
                upload_batch_id=upload_result["upload_batch_id"],
                source_file_id=file_summary["source_file_id"],
                filename=file_summary["filename"],
                source_text=file_summary["source_text"],
                source_origin="manual_upload",
                relative_path=file_summary.get("relative_path"),
            )
            for file_summary in upload_result["files"]
        ]

    response.status_code = 202
    return {
        "upload_batch_id": upload_result["upload_batch_id"],
        "jobs": [
            {"filename": file_summary["filename"], "job_run_id": job["job_run_id"]}
            for file_summary, job in zip(upload_result["files"], jobs)
        ],
    }


@router.post("/mainframe-pulls", status_code=202)
async def create_mainframe_pull(request: MainframePullBFFRequest, response: Response) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            pull_response = await client.post(f"{settings.source_mgmt_service_url}/mainframe-pulls", json=request.model_dump())
            pull_response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.json().get("detail", str(exc))) from exc
        pull_result = pull_response.json()

        job_result = await _trigger_job(
            client,
            project_id=request.project_id,
            upload_batch_id=pull_result["upload_batch_id"],
            source_file_id=pull_result["source_file_id"],
            filename=pull_result["filename"],
            source_text=pull_result["source_text"],
            source_origin="mainframe_scm",
        )

    response.status_code = 202
    return {"upload_batch_id": pull_result["upload_batch_id"], "job_run_id": job_result["job_run_id"]}


@router.get("/mainframe-elements")
async def list_mainframe_elements(project_id: str, tool: str, system: str, subsystem: str, element_type: str = "COBOL") -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{settings.source_mgmt_service_url}/mainframe-elements",
                params={"project_id": project_id, "tool": tool, "system": system, "subsystem": subsystem, "element_type": element_type},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.json().get("detail", str(exc))) from exc
        return response.json()
