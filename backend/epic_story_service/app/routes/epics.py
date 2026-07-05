"""GET /epics (list), GET /epics/{epic_id}/stories (children) — architecture.md section 2.2."""

from fastapi import APIRouter

from agents.common.mcp_client import get_mcp_client

router = APIRouter()


@router.get("/epics")
def list_epics(project_id: str, limit: int = 100) -> dict:
    mcp = get_mcp_client()
    result = mcp.couchdb_read(
        database="backlog", mango_selector={"project_id": project_id, "type": "epic"}, limit=limit
    )
    return {"items": result.get("docs", []), "bookmark": result.get("bookmark")}


@router.get("/epics/{epic_id}/stories")
def list_epic_stories(epic_id: str, project_id: str, limit: int = 100) -> dict:
    mcp = get_mcp_client()
    result = mcp.couchdb_read(
        database="backlog",
        mango_selector={"project_id": project_id, "type": "story", "epic_id": epic_id},
        limit=limit,
    )
    return {"items": result.get("docs", []), "bookmark": result.get("bookmark")}
