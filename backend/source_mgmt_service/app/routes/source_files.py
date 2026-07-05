"""GET /source-files/{source_file_id} — serves a persisted source_file doc
(architecture.md section 2.2), including its raw source_text if present.

Returns the doc as-is (source_text/relative_path may be null for source_file
docs written before those fields existed) rather than 404ing on a missing
field, so the caller can render its own "source not available" message
distinct from a real not-found/network error.
"""

from fastapi import APIRouter, HTTPException

from agents.common.mcp_client import get_mcp_client

router = APIRouter()


@router.get("/source-files/{source_file_id}")
def get_source_file(source_file_id: str, project_id: str) -> dict:
    mcp = get_mcp_client()
    result = mcp.couchdb_read(database="sources", doc_id=f"{project_id}:{source_file_id}:source_file")
    docs = result.get("docs", [])
    if not docs:
        raise HTTPException(status_code=404, detail="source file not found")
    return docs[0]
