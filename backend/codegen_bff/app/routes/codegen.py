"""GET /bff/codegen/eligible-stories, POST /bff/codegen/generate,
GET /bff/codegen/jobs/{job_run_id} (architecture.md sections 8, 9.1).

GET /codegen/eligible-stories fans out (asyncio.gather) epic-story-service
reads for every story in a project, plus a single unfiltered
recommendation-service read to build a program_id -> human_review_status
map (MigrationRecommendation.program_id is already denormalized for
exactly this lookup — see backend/review_bff/app/routes/review_items.py's
identical comment on the reverse join). A story is eligible only if EVERY
program in its source_program_ids maps to an approved recommendation —
one unapproved program blocks the whole story, since generated code would
otherwise be based in part on an unapproved target.

This list is deliberately NOT Redis-TTL-cached (unlike review_bff's
review-items list): approval state is exactly the kind of
just-clicked-Approve-and-switched-tabs event where a stale cache would be
actively confusing, and this endpoint's own re-verification at generation
time (agents/codegen/eligibility.py) is the real safety boundary anyway —
this list is a convenience view, not a security check.
"""

import asyncio
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/bff/codegen")

_RECOMMENDATIONS_FETCH_LIMIT = 500


class GenerateCodeRequest(BaseModel):
    project_id: str
    story_id: str
    target_language: Literal["python", "java_spring_boot"]


async def _fetch_all_stories(client: httpx.AsyncClient, project_id: str) -> list[dict]:
    epics_response = await client.get(f"{settings.epic_story_service_url}/epics", params={"project_id": project_id})
    epics_response.raise_for_status()
    epics = epics_response.json().get("items", [])
    epics_by_id = {epic["_id"]: epic for epic in epics}

    stories_responses = await asyncio.gather(
        *(
            client.get(f"{settings.epic_story_service_url}/epics/{epic['_id']}/stories", params={"project_id": project_id})
            for epic in epics
        )
    )

    stories: list[dict] = []
    for stories_response in stories_responses:
        stories_response.raise_for_status()
        for story in stories_response.json().get("items", []):
            story["_epic_title"] = epics_by_id.get(story["epic_id"], {}).get("title")
            stories.append(story)
    return stories


async def _fetch_recommendation_status_by_program_id(client: httpx.AsyncClient, project_id: str) -> dict[str, dict]:
    response = await client.get(
        f"{settings.recommendation_service_url}/recommendations",
        params={"project_id": project_id, "limit": _RECOMMENDATIONS_FETCH_LIMIT},
    )
    response.raise_for_status()
    recommendations = response.json().get("items", [])
    by_program_id: dict[str, dict] = {}
    for recommendation in recommendations:
        program_id = recommendation.get("program_id")
        if not program_id:
            continue
        existing = by_program_id.get(program_id)
        if existing is None or recommendation.get("updated_at", "") > existing.get("updated_at", ""):
            by_program_id[program_id] = recommendation
    return by_program_id


@router.get("/eligible-stories")
async def list_eligible_stories(project_id: str) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        stories, recommendation_by_program_id = await asyncio.gather(
            _fetch_all_stories(client, project_id),
            _fetch_recommendation_status_by_program_id(client, project_id),
        )

    items = []
    for story in stories:
        program_ids = story.get("source_program_ids", [])
        if not program_ids:
            continue
        recommendations = [recommendation_by_program_id.get(pid) for pid in program_ids]
        if any(r is None for r in recommendations):
            continue
        if not all(r.get("human_review_status") == "approved" for r in recommendations):
            continue
        items.append(
            {
                "story": story,
                "epic_title": story.get("_epic_title"),
                "recommended_targets": [r.get("recommended_target") for r in recommendations],
            }
        )

    return {"items": items}


@router.post("/generate", status_code=202)
async def generate_code(request: GenerateCodeRequest) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                f"{settings.job_pipeline_control_service_url}/jobs/generate-code",
                json=request.model_dump(),
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
        return response.json()


@router.get("/jobs/{job_run_id}")
async def get_codegen_job_status(job_run_id: str, project_id: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{settings.job_pipeline_control_service_url}/jobs/{job_run_id}", params={"project_id": project_id}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
        return response.json()
