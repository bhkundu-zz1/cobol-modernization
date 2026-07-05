"""kill.check / kill.set — the emergency kill-switch (architecture.md section 7).

Redis for fast in-memory checks, CouchDB job_run.kill_requested for
durability/audit. Fail-safe: if the check can't complete confidently,
treat as killed.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import redis

from ..config import settings
from ..schemas import (
    AuditActor,
    AuditAppendRequest,
    KillCheckRequest,
    KillCheckResult,
    KillSetRequest,
    KillSetResult,
)
from .audit_tools import audit_append

if TYPE_CHECKING:
    from ..couchdb_client import CouchDBClient

GLOBAL_KEY = "kill:global"


def _project_key(project_id: str) -> str:
    return f"kill:project:{project_id}"


def _job_key(job_run_id: str) -> str:
    return f"kill:job:{job_run_id}"


def get_redis_client() -> redis.Redis:
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        db=settings.redis_db_kill_flags,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def kill_check(
    redis_client: redis.Redis,
    couchdb_client: "CouchDBClient",
    request: KillCheckRequest,
) -> KillCheckResult:
    try:
        if redis_client.get(GLOBAL_KEY):
            return KillCheckResult(killed=True, reason="global kill flag set")
        if redis_client.get(_project_key(request.project_id)):
            return KillCheckResult(killed=True, reason=f"project {request.project_id} kill flag set")
        if redis_client.get(_job_key(request.job_run_id)):
            return KillCheckResult(killed=True, reason=f"job_run {request.job_run_id} kill flag set")
        return KillCheckResult(killed=False, reason=None)
    except redis.RedisError:
        pass

    # Redis unreachable — fall back to the durable CouchDB record.
    doc = couchdb_client.get_document(settings.couchdb_db_agent_runs, f"{request.project_id}:{request.job_run_id}:job_run")
    if doc is None:
        # Can't confirm state at all: fail-safe to killed, never "keep running" on uncertainty.
        return KillCheckResult(killed=True, reason="kill-switch state unreachable (redis and couchdb both failed)")
    return KillCheckResult(
        killed=bool(doc.get("kill_requested", False)),
        reason="couchdb fallback: job_run.kill_requested" if doc.get("kill_requested") else None,
    )


def kill_set(
    redis_client: redis.Redis,
    couchdb_client: "CouchDBClient",
    request: KillSetRequest,
) -> KillSetResult:
    now = datetime.now(timezone.utc).isoformat()

    if request.scope == "all":
        redis_client.set(GLOBAL_KEY, "1")
    elif request.scope == "project":
        assert request.scope_id, "scope_id is required for scope='project'"
        redis_client.set(_project_key(request.scope_id), "1")
    elif request.scope == "job_run":
        assert request.scope_id, "scope_id is required for scope='job_run'"
        redis_client.set(_job_key(request.scope_id), "1")

        job_run_doc: dict[str, Any] | None = None
        # job_run docs are keyed "<project_id>:<job_run_id>:job_run" by couchdb.write's
        # deterministic-id convention; without project_id here we do a Mango lookup.
        found = couchdb_client.find(
            settings.couchdb_db_agent_runs,
            selector={"type": "job_run", "job_run_id": request.scope_id},
            limit=1,
        )["docs"]
        if found:
            job_run_doc = found[0]
            job_run_doc["kill_requested"] = True
            job_run_doc["kill_requested_by"] = request.requested_by
            job_run_doc["kill_requested_at"] = now
            job_run_doc["updated_at"] = now
            couchdb_client.put_document(settings.couchdb_db_agent_runs, job_run_doc)

    audit_append(
        couchdb_client,
        AuditAppendRequest(
            project_id=request.scope_id if request.scope != "all" else "*",
            event_category="kill_switch",
            actor=AuditActor(kind="user", id=request.requested_by),
            action=f"kill_set(scope={request.scope}, scope_id={request.scope_id})",
            subject_doc_id=request.scope_id or "all",
            subject_doc_rev=None,
            before_state_hash=None,
            after_state_hash=None,
            model_used=None,
            skill_version_hash=None,
        ),
    )

    return KillSetResult(ok=True)
