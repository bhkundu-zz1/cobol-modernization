"""mainframe.fetch_source — read-only mainframe SCM connector (architecture.md section 1a).

Delegates to the adapter registry in agents/mainframe_ingestion/adapter.py
(Phase 3). This module is intentionally thin: it validates the request,
resolves the adapter, calls it, and logs the audit event — it never
constructs mock/real data itself.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

# agents/ lives as a sibling package to mcp_gateway/ in this monorepo; the
# adapter registry is implemented there since it's agent-facing domain logic,
# not gateway plumbing. Imported lazily (function-local) so mcp_gateway can
# still be imported/tested before Phase 3's agents/mainframe_ingestion exists.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ..config import settings
from ..schemas import (
    AuditActor,
    AuditAppendRequest,
    MainframeFetchSourceRequest,
    MainframeListResult,
    MainframePullResult,
)
from .audit_tools import audit_append

if TYPE_CHECKING:
    from ..couchdb_client import CouchDBClient


def _credential_ref_for(request: MainframeFetchSourceRequest) -> str:
    return request.credential_ref


def mainframe_fetch_source(
    couchdb_client: "CouchDBClient",
    request: MainframeFetchSourceRequest,
    requesting_agent: str,
    project_id: str,
) -> MainframeListResult | MainframePullResult:
    from agents.mainframe_ingestion.adapter import get_adapter  # noqa: PLC0415

    adapter = get_adapter(request.tool)

    if request.element_id is None:
        elements = adapter.list_elements(
            host=request.host,
            credential_ref=request.credential_ref,
            system=request.system,
            subsystem=request.subsystem,
            element_type=request.element_type,
        )
        result: dict[str, Any] = {"elements": elements}
        action = "mainframe_list_elements"
        outcome = MainframeListResult(elements=elements)
    else:
        source_text = adapter.get_source(
            host=request.host,
            credential_ref=request.credential_ref,
            system=request.system,
            subsystem=request.subsystem,
            element_type=request.element_type,
            element_id=request.element_id,
        )
        metadata = adapter.get_metadata(
            host=request.host,
            credential_ref=request.credential_ref,
            system=request.system,
            subsystem=request.subsystem,
            element_type=request.element_type,
            element_id=request.element_id,
        )
        action = "mainframe_pull_element"
        outcome = MainframePullResult(source_text=source_text, metadata=metadata)

    audit_append(
        couchdb_client,
        AuditAppendRequest(
            project_id=project_id,
            event_category="agent_output",
            actor=AuditActor(kind="agent", id=requesting_agent),
            action=action,
            subject_doc_id=request.element_id or f"{request.system}/{request.subsystem}",
            subject_doc_rev=None,
            before_state_hash=None,
            after_state_hash=None,
            model_used=None,
            skill_version_hash=None,
        ),
    )

    return outcome
