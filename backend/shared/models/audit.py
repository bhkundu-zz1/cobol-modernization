"""Audit log document model (architecture.md section 6.2).

This is the compliance record of truth — append-only, hash-chained.
Written exclusively via the MCP gateway's audit.append tool; no code path
in this repo should construct an AuditEvent and write it any other way.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from .envelope import DocEnvelope

AuditEventCategory = Literal[
    "agent_output",
    "human_review_decision",
    "guardrail_decision",
    "export",
    "kill_switch",
    "config_change",
]


class AuditActor(BaseModel):
    kind: Literal["agent", "user", "system"]
    id: str


class AuditEvent(DocEnvelope):
    model_config = {**DocEnvelope.model_config, "protected_namespaces": ()}

    type: Literal["audit_event"] = "audit_event"
    event_id: str
    event_category: AuditEventCategory
    actor: AuditActor
    action: str
    subject_doc_id: str
    subject_doc_rev: str | None = None
    before_state_hash: str | None = None
    after_state_hash: str | None = None
    model_used: str | None = None
    skill_version_hash: str | None = None
    timestamp: datetime
    prev_event_hash: str
    this_event_hash: str
