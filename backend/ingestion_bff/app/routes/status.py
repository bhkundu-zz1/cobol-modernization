"""GET /bff/jobs/{id} — proxies job-pipeline-control-service's job status, for UI polling."""

import httpx
from fastapi import APIRouter, HTTPException

from ..config import settings

router = APIRouter(prefix="/bff")


@router.get("/jobs/{job_run_id}")
async def get_job_status(job_run_id: str, project_id: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{settings.job_pipeline_control_service_url}/jobs/{job_run_id}", params={"project_id": project_id}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.json().get("detail", str(exc))) from exc
        return response.json()
