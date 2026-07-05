"""couchdb.read / couchdb.write — the only tools any agent uses to read or write CouchDB.

Per architecture.md section 1 ("Connection rules"): agents never hold a
CouchDB driver directly. See agents/tools/couchdb_tools.md for the
declaration doc consumed by skill authors.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from ..config import settings
from ..schemas import CouchDBReadRequest, CouchDBReadResult, CouchDBWriteRequest, CouchDBWriteResult

if TYPE_CHECKING:
    from ..couchdb_client import CouchDBClient


class AuditLogWriteRejected(Exception):
    """couchdb.write must not be used for the audit_log database — use audit.append."""


def deterministic_doc_id(project_id: str, source_file_id: str, doc_type: str) -> str:
    """Derives a stable _id for documents that are logically singular per
    (project_id, source_file_id, type), so a retried Celery task overwrites
    the same logical document rather than duplicating it (architecture.md section 9.2)."""
    return f"{project_id}:{source_file_id}:{doc_type}"


def couchdb_read(client: "CouchDBClient", request: CouchDBReadRequest) -> CouchDBReadResult:
    if request.doc_id is not None:
        doc = client.get_document(request.database, request.doc_id)
        return CouchDBReadResult(docs=[doc] if doc else [], bookmark=None)

    selector = request.mango_selector or {}
    result = client.find(request.database, selector, limit=request.limit)
    return CouchDBReadResult(**result)


def couchdb_write(client: "CouchDBClient", request: CouchDBWriteRequest) -> CouchDBWriteResult:
    if request.database == settings.couchdb_db_audit_log:
        raise AuditLogWriteRejected(
            "couchdb.write does not accept database='audit_log'; use audit.append instead."
        )

    doc: dict[str, Any] = dict(request.doc)
    now = datetime.now(timezone.utc).isoformat()
    doc.setdefault("schema_version", 1)
    doc["project_id"] = request.project_id
    doc.setdefault("created_at", now)
    doc["created_by"] = request.created_by
    doc["updated_at"] = now
    doc["trace_id"] = request.trace_id

    # Idempotent write: if the caller's doc shape includes source_file_id and
    # type, derive a deterministic _id so retries overwrite instead of duplicate.
    if "_id" not in doc and "source_file_id" in doc and "type" in doc:
        candidate_id = deterministic_doc_id(request.project_id, doc["source_file_id"], doc["type"])
        existing = client.get_document(request.database, candidate_id)
        if existing is not None:
            doc["_id"] = candidate_id
            doc["_rev"] = existing["_rev"]
        else:
            doc["_id"] = candidate_id

    result = client.put_document(request.database, doc)
    return CouchDBWriteResult(**result)
