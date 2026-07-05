"""PATCH /stories/{story_id} — human edits to a generated story (architecture.md section 2.2).

Sets edited_by_human=True and appends to edit_history_ref, using the
audit.append call's returned event_id as the history entry — reuses the
audit log as the edit-history store rather than inventing a second one.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.common.mcp_client import get_mcp_client

router = APIRouter()


class StoryPatchRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    acceptance_criteria: list[str] | None = None
    edited_by: str


@router.patch("/stories/{story_id}")
def update_story(story_id: str, request: StoryPatchRequest) -> dict:
    mcp = get_mcp_client()
    existing = mcp.couchdb_read(database="backlog", doc_id=story_id)
    docs = existing.get("docs", [])
    if not docs:
        raise HTTPException(status_code=404, detail="story not found")

    doc = docs[0]
    before_title = doc.get("title")

    if request.title is not None:
        doc["title"] = request.title
    if request.description is not None:
        doc["description"] = request.description
    if request.acceptance_criteria is not None:
        doc["acceptance_criteria"] = request.acceptance_criteria
    doc["edited_by_human"] = True

    audit_result = mcp.audit_append(
        project_id=doc["project_id"],
        event_category="human_review_decision",
        actor={"kind": "user", "id": request.edited_by},
        action="story_edited",
        subject_doc_id=story_id,
        subject_doc_rev=doc.get("_rev"),
        before_state_hash=before_title,
        after_state_hash=doc.get("title"),
    )
    doc.setdefault("edit_history_ref", [])
    doc["edit_history_ref"].append(audit_result["id"])

    write_result = mcp.couchdb_write(
        database="backlog",
        doc=doc,
        project_id=doc["project_id"],
        created_by=f"user:{request.edited_by}",
        trace_id=story_id,
    )

    return {"story_id": write_result["id"], "edited_by_human": True, "edit_history_ref": doc["edit_history_ref"]}
