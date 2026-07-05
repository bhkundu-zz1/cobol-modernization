"""POST /export — delegates to the MCP gateway's issue_tracker.export tool
(docs/architecture.md section 1b)."""

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.common.mcp_client import get_mcp_client

router = APIRouter()


class ExportRequest(BaseModel):
    project_id: str
    tool: Literal["github", "jira"]
    connection_config: dict[str, Any]
    epic_ids: list[str]
    story_ids: list[str]
    requesting_agent: str = "editor-mfe-user"


@router.post("/export")
def export_items(request: ExportRequest) -> dict:
    mcp = get_mcp_client()
    try:
        return mcp.issue_tracker_export(
            tool=request.tool,
            connection_config=request.connection_config,
            epic_ids=request.epic_ids,
            story_ids=request.story_ids,
            requesting_agent=request.requesting_agent,
            project_id=request.project_id,
        )
    except Exception as exc:  # noqa: BLE001 - real (non-github) tools raise NotImplementedError; surfaced as 501, never silently faked
        raise HTTPException(
            status_code=501,
            detail=f"{exc} (selecting a destination before its export protocol is implemented)",
        ) from exc
