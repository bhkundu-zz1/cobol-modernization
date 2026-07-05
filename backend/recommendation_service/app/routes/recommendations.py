"""GET /recommendations (list/filter), POST /recommendations/{id}/decision
(architecture.md section 2.2)."""

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.common.mcp_client import get_mcp_client

router = APIRouter()


class DecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    reviewed_by: str
    comment: str | None = None


@router.get("/recommendations")
def list_recommendations(
    project_id: str,
    human_review_status: str | None = None,
    min_confidence: float | None = None,
    limit: int = 50,
) -> dict:
    mcp = get_mcp_client()
    selector: dict = {"project_id": project_id, "type": "migration_recommendation"}
    if human_review_status is not None:
        selector["human_review_status"] = human_review_status

    result = mcp.couchdb_read(database="recommendations", mango_selector=selector, limit=limit)
    docs = result.get("docs", [])
    if min_confidence is not None:
        docs = [d for d in docs if d.get("confidence_score", 0) >= min_confidence]

    return {"items": docs, "bookmark": result.get("bookmark")}


@router.get("/recommendations/{recommendation_id}")
def get_recommendation(recommendation_id: str) -> dict:
    mcp = get_mcp_client()
    result = mcp.couchdb_read(database="recommendations", doc_id=recommendation_id)
    docs = result.get("docs", [])
    if not docs:
        raise HTTPException(status_code=404, detail="recommendation not found")
    return docs[0]


@router.post("/recommendations/{recommendation_id}/decision")
def record_decision(recommendation_id: str, request: DecisionRequest) -> dict:
    mcp = get_mcp_client()
    existing = mcp.couchdb_read(database="recommendations", doc_id=recommendation_id)
    docs = existing.get("docs", [])
    if not docs:
        raise HTTPException(status_code=404, detail="recommendation not found")

    doc = docs[0]
    before_status = doc.get("human_review_status")
    doc["human_review_status"] = request.decision
    doc["reviewed_by"] = request.reviewed_by
    doc["reviewed_at"] = datetime.now(timezone.utc).isoformat()

    write_result = mcp.couchdb_write(
        database="recommendations",
        doc=doc,
        project_id=doc["project_id"],
        created_by=f"user:{request.reviewed_by}",
        trace_id=recommendation_id,
    )

    mcp.audit_append(
        project_id=doc["project_id"],
        event_category="human_review_decision",
        actor={"kind": "user", "id": request.reviewed_by},
        action=f"recommendation_{request.decision}",
        subject_doc_id=write_result["id"],
        subject_doc_rev=write_result.get("rev"),
        before_state_hash=before_status,
        after_state_hash=request.decision,
    )

    return {"recommendation_id": write_result["id"], "human_review_status": request.decision}
