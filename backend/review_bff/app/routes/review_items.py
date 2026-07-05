"""GET /bff/review-items, POST /bff/review-items/{id}/decision, GET
/bff/review-items/{id}/source, GET /bff/review-items/{id}/backlog, POST
/bff/generate-epics-stories (architecture.md sections 8, 9.1).

GET /review-items fans out (asyncio.gather) recommendation-service reads for
the recommendation list plus, per recommendation, the owning job_run's
status from job-pipeline-control-service — concurrent, not serial, so the
BFF's own response time stays well under the <5s NFR budget even as the
number of in-flight jobs grows. Result is Redis-TTL-cached (see cache.py for
the explicit staleness tradeoff this implies).

The new per-row source/backlog routes are deliberately NOT part of that
list fan-out or its cache: full COBOL source text and backlog lookups are
fetched only on demand when a reviewer expands a specific row (mirroring
the Editor MFE's lazy-expand pattern), since fetching them for every row on
every list load would bloat the cached list payload and threaten the <5s
NFR for no benefit to rows nobody expands.
"""

import asyncio
import json

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..cache import get_cached, get_redis_client, invalidate, set_cached
from ..config import settings

router = APIRouter(prefix="/bff")


class DecisionRequest(BaseModel):
    decision: str
    reviewed_by: str
    comment: str | None = None


class GenerateEpicsStoriesRequest(BaseModel):
    project_id: str


def _cache_key(project_id: str, human_review_status: str | None) -> str:
    return f"review-items:{project_id}:{human_review_status or 'all'}"


async def _fetch_recommendations(client: httpx.AsyncClient, project_id: str, human_review_status: str | None) -> dict:
    params = {"project_id": project_id}
    if human_review_status is not None:
        params["human_review_status"] = human_review_status
    response = await client.get(f"{settings.recommendation_service_url}/recommendations", params=params)
    response.raise_for_status()
    return response.json()


async def _fetch_job_status(client: httpx.AsyncClient, project_id: str, job_run_id: str) -> dict | None:
    try:
        response = await client.get(
            f"{settings.job_pipeline_control_service_url}/jobs/{job_run_id}", params={"project_id": project_id}
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError:
        return None


@router.get("/review-items")
async def list_review_items(project_id: str, human_review_status: str | None = None, min_confidence: float | None = None) -> dict:
    cache_key = _cache_key(project_id, human_review_status)
    redis_client = get_redis_client()
    cached = get_cached(redis_client, cache_key)
    if cached is not None:
        return cached

    async with httpx.AsyncClient(timeout=15.0) as client:
        recommendations_result = await _fetch_recommendations(client, project_id, human_review_status)
        recommendations = recommendations_result.get("items", [])
        if min_confidence is not None:
            recommendations = [r for r in recommendations if r.get("confidence_score", 0) >= min_confidence]

        # Concurrent fan-out: one job-status lookup per distinct job_run,
        # not serial round-trips per recommendation.
        job_run_ids = {r.get("job_run_id") for r in recommendations if r.get("job_run_id")}
        job_statuses = await asyncio.gather(*(_fetch_job_status(client, project_id, jr_id) for jr_id in job_run_ids))
        job_status_by_id = {jr_id: status for jr_id, status in zip(job_run_ids, job_statuses) if status is not None}

    items = [
        {
            "subject_id": r.get("subject_id"),
            "subject_filename": r.get("subject_filename"),
            "subject_type": r.get("subject_type"),
            "recommendation": r,
            "confidence_score": r.get("confidence_score"),
            "needs_human_review": r.get("confidence_score", 1.0) < 0.7,
            "job_run_status": job_status_by_id.get(r.get("job_run_id"), {}).get("status"),
            "human_review_status": r.get("human_review_status"),
        }
        for r in recommendations
    ]

    result = {"items": items, "bookmark": recommendations_result.get("bookmark")}
    set_cached(redis_client, cache_key, result)
    return result


@router.post("/review-items/{recommendation_id}/decision")
async def record_decision(recommendation_id: str, request: DecisionRequest, project_id: str) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                f"{settings.recommendation_service_url}/recommendations/{recommendation_id}/decision",
                json=request.model_dump(),
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
        result = response.json()

    redis_client = get_redis_client()
    invalidate(redis_client, f"review-items:{project_id}:")

    return result


@router.get("/review-items/{recommendation_id}/source")
async def get_review_item_source(recommendation_id: str, project_id: str) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            recommendation_response = await client.get(
                f"{settings.recommendation_service_url}/recommendations/{recommendation_id}"
            )
            recommendation_response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
        recommendation = recommendation_response.json()

        source_file_id = recommendation.get("source_file_id")
        if not source_file_id:
            return {"filename": None, "source_text": None, "relative_path": None, "language": None}

        try:
            source_response = await client.get(
                f"{settings.source_mgmt_service_url}/source-files/{source_file_id}", params={"project_id": project_id}
            )
            source_response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
        source_file = source_response.json()

    return {
        "filename": source_file.get("filename"),
        "source_text": source_file.get("source_text"),
        "relative_path": source_file.get("relative_path"),
        "language": source_file.get("language"),
    }


@router.get("/review-items/{recommendation_id}/backlog")
async def get_review_item_backlog(recommendation_id: str, project_id: str) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            recommendation_response = await client.get(
                f"{settings.recommendation_service_url}/recommendations/{recommendation_id}"
            )
            recommendation_response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
        recommendation = recommendation_response.json()

        # story.source_program_ids stores program_id (e.g. "PAYROLL01" —
        # see agents/epic_story_writer/task.py), which is denormalized onto
        # the recommendation doc as program_id for exactly this lookup (see
        # agents/recommendation/task.py and backend/shared/models/recommendation.py).
        program_id = recommendation.get("program_id")

        epics_response = await client.get(f"{settings.epic_story_service_url}/epics", params={"project_id": project_id})
        epics_response.raise_for_status()
        epics = epics_response.json().get("items", [])

        stories_lists = await asyncio.gather(
            *(
                client.get(
                    f"{settings.epic_story_service_url}/epics/{epic['_id']}/stories", params={"project_id": project_id}
                )
                for epic in epics
            )
        )

    epics_by_id = {epic["_id"]: epic for epic in epics}
    for stories_response in stories_lists:
        stories_response.raise_for_status()
        for story in stories_response.json().get("items", []):
            if program_id in story.get("source_program_ids", []):
                epic = epics_by_id.get(story["epic_id"])
                return {"epic": epic, "story": story}

    return {"epic": None, "story": None}


@router.post("/generate-epics-stories", status_code=202)
async def generate_epics_stories(request: GenerateEpicsStoriesRequest) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                f"{settings.job_pipeline_control_service_url}/jobs/generate-epics-stories",
                json={"project_id": request.project_id},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
        return response.json()


@router.get("/jobs/{job_run_id}")
async def get_job_status(job_run_id: str, project_id: str) -> dict:
    """Proxies job-pipeline-control-service's job status — used by the
    Review Queue to poll the "Generate Epics & Stories" job_run, mirroring
    ingestion_bff's identical route for upload job polling."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{settings.job_pipeline_control_service_url}/jobs/{job_run_id}", params={"project_id": project_id}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
        return response.json()
