"""Verifies the audit log's hash-chain tamper-evidence: this is the concrete
proof of architecture.md section 6.2's compliance claim, not just "a hash
field exists somewhere"."""

from datetime import datetime, timedelta, timezone

from app.hashing import GENESIS_HASH, verify_chain
from app.schemas import AuditActor, AuditAppendRequest, AuditExportRangeRequest
from app.tools.audit_tools import audit_append, audit_export_range


def _append(fake_couchdb, project_id="acme-2026", action="created_recommendation"):
    return audit_append(
        fake_couchdb,
        AuditAppendRequest(
            project_id=project_id,
            event_category="agent_output",
            actor=AuditActor(kind="agent", id="recommendation-agent@v1"),
            action=action,
            subject_doc_id="doc-1",
            subject_doc_rev="1-abc",
            before_state_hash=None,
            after_state_hash="deadbeef",
            model_used="cobol-analysis-dev",
            skill_version_hash="skillhash123",
        ),
    )


def test_first_event_chains_from_genesis(fake_couchdb):
    result = _append(fake_couchdb)
    docs = fake_couchdb.find("audit_log", {"type": "audit_event"})["docs"]
    assert len(docs) == 1
    assert docs[0]["prev_event_hash"] == GENESIS_HASH
    assert docs[0]["this_event_hash"] == result.this_event_hash


def test_second_event_chains_from_first(fake_couchdb):
    first = _append(fake_couchdb)
    second = _append(fake_couchdb, action="approved_recommendation")

    assert second != first
    docs = fake_couchdb.find("audit_log", {"type": "audit_event"})["docs"]
    docs_sorted = sorted(docs, key=lambda d: d["timestamp"])
    assert docs_sorted[1]["prev_event_hash"] == first.this_event_hash


def test_export_range_reports_valid_chain(fake_couchdb):
    _append(fake_couchdb)
    _append(fake_couchdb, action="approved_recommendation")

    start = datetime.now(timezone.utc) - timedelta(hours=1)
    end = datetime.now(timezone.utc) + timedelta(hours=1)
    result = audit_export_range(fake_couchdb, AuditExportRangeRequest(project_id="acme-2026", start=start, end=end))

    assert len(result.events) == 2
    assert result.chain_valid is True


def test_tampering_a_past_event_breaks_the_chain(fake_couchdb):
    _append(fake_couchdb)
    _append(fake_couchdb, action="approved_recommendation")

    docs = fake_couchdb.find("audit_log", {"type": "audit_event"})["docs"]
    docs_sorted = sorted(docs, key=lambda d: d["timestamp"])
    tampered = docs_sorted[0]

    assert verify_chain(docs_sorted) is True, "sanity check: chain is valid before tampering"

    # Simulate a compromised admin directly editing CouchDB, bypassing audit.append entirely.
    tampered["action"] = "created_recommendation_TAMPERED"
    docs_sorted[0] = tampered

    assert verify_chain(docs_sorted) is False, "tampering a past event must break the chain"
