"""MCP gateway — FastMCP server bootstrap.

Exposes couchdb.read, couchdb.write, audit.append, audit.export_range,
kill.check, kill.set, mainframe.fetch_source, and issue_tracker.export as
MCP tools. This process is the only path from agent code to CouchDB, the
audit log, the kill-switch state, the mainframe connector, or the
issue-tracker export mechanism (architecture.md section 1).
"""

from datetime import datetime
from typing import Any

from fastmcp import FastMCP

from .config import settings
from .couchdb_client import get_couchdb_client
from .schemas import (
    AuditActor,
    AuditAppendRequest,
    AuditExportRangeRequest,
    CouchDBReadRequest,
    CouchDBWriteRequest,
    IssueTrackerExportRequest,
    KillCheckRequest,
    KillSetRequest,
    MainframeFetchSourceRequest,
)
from .tools.audit_tools import audit_append as _audit_append
from .tools.audit_tools import audit_export_range as _audit_export_range
from .tools.couchdb_tools import couchdb_read as _couchdb_read
from .tools.couchdb_tools import couchdb_write as _couchdb_write
from .tools.export_tools import issue_tracker_export as _issue_tracker_export
from .tools.kill_tools import get_redis_client, kill_check as _kill_check, kill_set as _kill_set
from .tools.mainframe_tools import mainframe_fetch_source as _mainframe_fetch_source

mcp = FastMCP("cobol-migration-mcp-gateway")


@mcp.tool()
def couchdb_read(
    database: str,
    doc_id: str | None = None,
    mango_selector: dict[str, Any] | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    client = get_couchdb_client()
    request = CouchDBReadRequest(database=database, doc_id=doc_id, mango_selector=mango_selector, limit=limit)
    return _couchdb_read(client, request).model_dump()


@mcp.tool()
def couchdb_write(
    database: str,
    doc: dict[str, Any],
    project_id: str,
    created_by: str,
    trace_id: str,
) -> dict[str, Any]:
    client = get_couchdb_client()
    request = CouchDBWriteRequest(
        database=database, doc=doc, project_id=project_id, created_by=created_by, trace_id=trace_id
    )
    return _couchdb_write(client, request).model_dump()


@mcp.tool()
def audit_append(
    project_id: str,
    event_category: str,
    actor: dict[str, str],
    action: str,
    subject_doc_id: str,
    subject_doc_rev: str | None = None,
    before_state_hash: str | None = None,
    after_state_hash: str | None = None,
    model_used: str | None = None,
    skill_version_hash: str | None = None,
) -> dict[str, Any]:
    client = get_couchdb_client()
    request = AuditAppendRequest(
        project_id=project_id,
        event_category=event_category,  # type: ignore[arg-type]
        actor=AuditActor(**actor),
        action=action,
        subject_doc_id=subject_doc_id,
        subject_doc_rev=subject_doc_rev,
        before_state_hash=before_state_hash,
        after_state_hash=after_state_hash,
        model_used=model_used,
        skill_version_hash=skill_version_hash,
    )
    return _audit_append(client, request).model_dump()


@mcp.tool()
def audit_export_range(project_id: str, start: str, end: str) -> dict[str, Any]:
    client = get_couchdb_client()
    request = AuditExportRangeRequest(project_id=project_id, start=datetime.fromisoformat(start), end=datetime.fromisoformat(end))
    return _audit_export_range(client, request).model_dump()


@mcp.tool()
def kill_check(project_id: str, job_run_id: str) -> dict[str, Any]:
    redis_client = get_redis_client()
    couchdb_client = get_couchdb_client()
    request = KillCheckRequest(project_id=project_id, job_run_id=job_run_id)
    return _kill_check(redis_client, couchdb_client, request).model_dump()


@mcp.tool()
def kill_set(scope: str, requested_by: str, scope_id: str | None = None) -> dict[str, Any]:
    redis_client = get_redis_client()
    couchdb_client = get_couchdb_client()
    request = KillSetRequest(scope=scope, scope_id=scope_id, requested_by=requested_by)  # type: ignore[arg-type]
    return _kill_set(redis_client, couchdb_client, request).model_dump()


@mcp.tool()
def mainframe_fetch_source(
    tool: str,
    host: str,
    credential_ref: str,
    system: str,
    subsystem: str,
    element_type: str,
    requesting_agent: str,
    project_id: str,
    element_id: str | None = None,
) -> dict[str, Any]:
    client = get_couchdb_client()
    request = MainframeFetchSourceRequest(
        tool=tool,  # type: ignore[arg-type]
        host=host,
        credential_ref=credential_ref,
        system=system,
        subsystem=subsystem,
        element_type=element_type,
        element_id=element_id,
    )
    result = _mainframe_fetch_source(client, request, requesting_agent=requesting_agent, project_id=project_id)
    return result.model_dump()


@mcp.tool()
def issue_tracker_export(
    tool: str,
    connection_config: dict[str, Any],
    epic_ids: list[str],
    story_ids: list[str],
    requesting_agent: str,
    project_id: str,
) -> dict[str, Any]:
    client = get_couchdb_client()
    request = IssueTrackerExportRequest(
        tool=tool,  # type: ignore[arg-type]
        connection_config=connection_config,
        epic_ids=epic_ids,
        story_ids=story_ids,
    )
    result = _issue_tracker_export(client, request, requesting_agent=requesting_agent, project_id=project_id)
    return result.model_dump()


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=settings.mcp_gateway_port)
