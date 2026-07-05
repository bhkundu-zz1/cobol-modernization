"""POST /mainframe-pulls — triggers a mainframe SCM connector pull via MCP
(architecture.md section 1a). Produces the same source_upload/source_file
shape as manual upload, with source_origin="mainframe_scm" and a populated
scm_element_ref.
"""

import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.common.mcp_client import get_mcp_client

from ..config import settings

router = APIRouter()

_CREDENTIAL_REFS = {
    "endevor": settings.mainframe_endevor_credential_ref,
    "panvalet": settings.mainframe_panvalet_credential_ref,
    "changeman": settings.mainframe_changeman_credential_ref,
    "mock": "vault://mainframe/mock/readonly",
}

_HOSTS = {
    "endevor": settings.mainframe_endevor_host,
    "panvalet": settings.mainframe_panvalet_host,
    "changeman": settings.mainframe_changeman_host,
    "mock": "mock-host",
}


class MainframePullRequest(BaseModel):
    project_id: str
    tool: Literal["endevor", "panvalet", "changeman", "mock"]
    system: str
    subsystem: str
    element_type: str = "COBOL"
    element_id: str


@router.get("/mainframe-elements")
def list_mainframe_elements(
    project_id: str, tool: Literal["endevor", "panvalet", "changeman", "mock"], system: str, subsystem: str, element_type: str = "COBOL"
) -> dict:
    mcp = get_mcp_client()
    try:
        result = mcp.mainframe_fetch_source(
            tool=tool,
            host=_HOSTS[tool],
            credential_ref=_CREDENTIAL_REFS[tool],
            system=system,
            subsystem=subsystem,
            element_type=element_type,
            requesting_agent="source-mgmt-service",
            project_id=project_id,
        )
    except Exception as exc:  # noqa: BLE001 - surfaced verbatim to the caller, see below
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return result


@router.post("/mainframe-pulls")
def create_mainframe_pull(request: MainframePullRequest) -> dict:
    mcp = get_mcp_client()

    try:
        pull_result = mcp.mainframe_fetch_source(
            tool=request.tool,
            host=_HOSTS[request.tool],
            credential_ref=_CREDENTIAL_REFS[request.tool],
            system=request.system,
            subsystem=request.subsystem,
            element_type=request.element_type,
            element_id=request.element_id,
            requesting_agent="source-mgmt-service",
            project_id=request.project_id,
        )
    except Exception as exc:  # noqa: BLE001 - real (non-mock) tools raise NotImplementedError; surfaced as 501, never silently mocked
        raise HTTPException(
            status_code=501,
            detail=f"{exc} (selecting a real, non-mock tool before its wire protocol is implemented)",
        ) from exc

    upload_batch_id = str(uuid.uuid4())
    source_file_id = str(uuid.uuid4())

    upload_write = mcp.couchdb_write(
        database="sources",
        doc={
            "type": "source_upload",
            "upload_batch_id": upload_batch_id,
            "uploaded_by": f"connector:mainframe-{request.tool}",
            "source_origin": "mainframe_scm",
            "file_count": 1,
            "total_bytes": len(pull_result["source_text"].encode("utf-8")),
            "status": "received",
            "secret_scan_result": {"flagged_files": [], "scan_passed": False},
        },
        project_id=request.project_id,
        created_by=f"connector:mainframe-{request.tool}",
        trace_id=upload_batch_id,
    )

    return {
        "upload_batch_id": upload_batch_id,
        "source_upload_id": upload_write["id"],
        "source_file_id": source_file_id,
        "filename": f"{request.element_id}.CBL",
        "source_text": pull_result["source_text"],
        "scm_element_ref": pull_result["metadata"],
    }
