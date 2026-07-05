"""GET /bff/epics, GET /bff/epics/{epic_id}/stories, PATCH /bff/stories/{id},
POST /bff/export (architecture.md sections 8, 9.1).

Straight proxies to epic_story_service — source_program_ids are already
human-readable strings (e.g. "PAYROLL01:2000-CALC-GROSS") in the underlying
Story documents, so no enrichment fan-out is needed here, unlike review_bff's
job-status fan-out. Still routed through this BFF layer rather than letting
the browser call epic_story_service directly, per the "browser never talks
to Core API services directly" rule.
"""

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/bff")


class StoryPatchRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    acceptance_criteria: list[str] | None = None
    edited_by: str


class ExportRequest(BaseModel):
    project_id: str
    tool: str
    connection_config: dict[str, Any]
    epic_ids: list[str]
    story_ids: list[str]
    requesting_agent: str = "editor-mfe-user"


@router.get("/epics")
async def list_epics(project_id: str, limit: int = 100) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{settings.epic_story_service_url}/epics", params={"project_id": project_id, "limit": limit}
        )
        response.raise_for_status()
        return response.json()


@router.get("/epics/{epic_id}/stories")
async def list_epic_stories(epic_id: str, project_id: str, limit: int = 100) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{settings.epic_story_service_url}/epics/{epic_id}/stories",
            params={"project_id": project_id, "limit": limit},
        )
        response.raise_for_status()
        return response.json()


@router.patch("/stories/{story_id}")
async def update_story(story_id: str, request: StoryPatchRequest) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.patch(
                f"{settings.epic_story_service_url}/stories/{story_id}", json=request.model_dump()
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
        return response.json()


@router.post("/export")
async def export_items(request: ExportRequest) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(f"{settings.epic_story_service_url}/export", json=request.model_dump())
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
        return response.json()
