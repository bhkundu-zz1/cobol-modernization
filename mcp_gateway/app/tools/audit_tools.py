"""audit.append / audit.export_range — the compliance record of truth (architecture.md section 6.2).

Real sha256 hash chaining, not stubbed. This tool exposes no update or
delete method at all — append-only by construction, not merely guarded.
See agents/tools/audit_tool.md for the declaration doc.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ..config import settings
from ..hashing import GENESIS_HASH, compute_event_hash, verify_chain
from ..schemas import (
    AuditAppendRequest,
    AuditAppendResult,
    AuditExportRangeRequest,
    AuditExportRangeResult,
)

if TYPE_CHECKING:
    from ..couchdb_client import CouchDBClient


def _latest_event_hash(client: "CouchDBClient", project_id: str) -> str:
    result = client.find(
        settings.couchdb_db_audit_log,
        selector={"project_id": project_id, "type": "audit_event"},
        limit=1,
    )
    # Mango doesn't sort by default without an index hint here; callers of
    # this gateway create the {job_run_id asc, started_at asc}-style index
    # from architecture.md section 2.3, but for the audit chain specifically
    # we need strict recency, so fetch a bounded window and pick the max
    # timestamp. Kept simple and correct for this pass's data volumes.
    docs = client.find(
        settings.couchdb_db_audit_log,
        selector={"project_id": project_id, "type": "audit_event"},
        limit=1000,
    )["docs"]
    if not docs:
        return GENESIS_HASH
    latest = max(docs, key=lambda d: d["timestamp"])
    return latest["this_event_hash"]


def audit_append(client: "CouchDBClient", request: AuditAppendRequest) -> AuditAppendResult:
    prev_hash = _latest_event_hash(client, request.project_id)
    timestamp = datetime.now(timezone.utc)

    event_payload = {
        "type": "audit_event",
        "schema_version": 1,
        "project_id": request.project_id,
        "event_id": str(uuid.uuid4()),
        "event_category": request.event_category,
        "actor": request.actor.model_dump(),
        "action": request.action,
        "subject_doc_id": request.subject_doc_id,
        "subject_doc_rev": request.subject_doc_rev,
        "before_state_hash": request.before_state_hash,
        "after_state_hash": request.after_state_hash,
        "model_used": request.model_used,
        "skill_version_hash": request.skill_version_hash,
        "timestamp": timestamp.isoformat(),
        "prev_event_hash": prev_hash,
        "created_by": request.actor.id,
        "created_at": timestamp.isoformat(),
        "updated_at": timestamp.isoformat(),
        "trace_id": request.subject_doc_id,
    }
    this_hash = compute_event_hash(
        {k: v for k, v in event_payload.items()},
        prev_hash,
    )
    event_payload["this_event_hash"] = this_hash
    event_payload["_id"] = f"{request.project_id}:audit:{event_payload['event_id']}"

    result = client.put_document(settings.couchdb_db_audit_log, event_payload)
    return AuditAppendResult(id=result["id"], rev=result["rev"], this_event_hash=this_hash)


def audit_export_range(client: "CouchDBClient", request: AuditExportRangeRequest) -> AuditExportRangeResult:
    docs = client.find(
        settings.couchdb_db_audit_log,
        selector={
            "project_id": request.project_id,
            "type": "audit_event",
            "timestamp": {"$gte": request.start.isoformat(), "$lte": request.end.isoformat()},
        },
        limit=10000,
    )["docs"]
    docs_sorted = sorted(docs, key=lambda d: d["timestamp"])
    return AuditExportRangeResult(events=docs_sorted, chain_valid=verify_chain(docs_sorted))
