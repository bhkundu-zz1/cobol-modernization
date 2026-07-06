"""Server-side re-verification of a story's code-generation eligibility.

The Code Generation tab's list view (owned by codegen_bff, a separate
Python process) performs the same join for display purposes, but that
check can go stale between when a user loads the list and when they click
Generate. This module is the authoritative, task-time re-check: never
trust that the frontend's eligibility check is still fresh.
"""

from agents.common.mcp_client import MCPClient


class ApprovalGateError(Exception):
    """Raised when a story's source program's migration_recommendation is
    not human_review_status == "approved" at generation time."""


def resolve_approved_recommendation(mcp: MCPClient, project_id: str, program_id: str) -> dict:
    """Returns an approved migration_recommendation for `program_id`, or
    raises ApprovalGateError if none exists or none is approved.

    `program_id` is not guaranteed unique per project (repeated uploads of
    the same or similarly-named program produce multiple
    cobol_program_structure/migration_recommendation docs sharing one
    program_id) — this reads every matching structure/recommendation
    rather than trusting an arbitrary limit=1 pick, and requires at least
    one to be approved. If more than one is approved, the most recently
    updated is used (best-effort disambiguation; the underlying data model
    doesn't carry a story -> specific-structure reference to resolve this
    unambiguously)."""
    structure_result = mcp.couchdb_read(
        database="parsed_structure",
        mango_selector={"project_id": project_id, "type": "cobol_program_structure", "program_id": program_id},
        limit=500,
    )
    structure_docs = structure_result.get("docs", [])
    if not structure_docs:
        raise ApprovalGateError(f"no cobol_program_structure found for program_id={program_id!r}")

    approved_recommendations: list[dict] = []
    latest_status: str | None = None
    for structure in structure_docs:
        recommendation_result = mcp.couchdb_read(
            database="recommendations",
            mango_selector={"project_id": project_id, "type": "migration_recommendation", "subject_id": structure["_id"]},
            limit=1,
        )
        recommendation_docs = recommendation_result.get("docs", [])
        if not recommendation_docs:
            continue
        recommendation = recommendation_docs[0]
        latest_status = recommendation.get("human_review_status")
        if latest_status == "approved":
            approved_recommendations.append(recommendation)

    if not approved_recommendations:
        raise ApprovalGateError(
            f"program_id={program_id!r} has no approved migration_recommendation "
            f"(most recently seen status: {latest_status!r})"
        )

    approved_recommendations.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
    return approved_recommendations[0]
