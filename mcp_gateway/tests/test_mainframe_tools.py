"""Exercises mainframe.fetch_source against the mock adapter end-to-end.

Depends on agents/mainframe_ingestion/adapter.py (Phase 3) for the adapter
registry and MockAdapter. Skipped automatically if that module doesn't
exist yet, so this file can land in Phase 2 per the plan without blocking
Phase 2's own test run.
"""

import pytest

pytest.importorskip("agents.mainframe_ingestion.adapter", reason="Phase 3 not yet implemented")

from app.schemas import MainframeFetchSourceRequest
from app.tools.mainframe_tools import mainframe_fetch_source


def test_mock_adapter_list_elements(fake_couchdb):
    request = MainframeFetchSourceRequest(
        tool="mock",
        host="mock-host",
        credential_ref="vault://mainframe/mock/readonly",
        system="PAYSYS",
        subsystem="PAYROLL",
        element_type="COBOL",
    )
    result = mainframe_fetch_source(fake_couchdb, request, requesting_agent="test-agent", project_id="acme-2026")
    assert any(e.element_id == "PAYROLL01" for e in result.elements)


def test_mock_adapter_pull_element_matches_fixture(fake_couchdb):
    request = MainframeFetchSourceRequest(
        tool="mock",
        host="mock-host",
        credential_ref="vault://mainframe/mock/readonly",
        system="PAYSYS",
        subsystem="PAYROLL",
        element_type="COBOL",
        element_id="PAYROLL01",
    )
    result = mainframe_fetch_source(fake_couchdb, request, requesting_agent="test-agent", project_id="acme-2026")
    assert "PROGRAM-ID. PAYROLL01" in result.source_text
    assert result.metadata["element_id"] == "PAYROLL01"


def test_mock_adapter_pull_logs_audit_event(fake_couchdb):
    request = MainframeFetchSourceRequest(
        tool="mock",
        host="mock-host",
        credential_ref="vault://mainframe/mock/readonly",
        system="PAYSYS",
        subsystem="PAYROLL",
        element_type="COBOL",
        element_id="PAYROLL01",
    )
    mainframe_fetch_source(fake_couchdb, request, requesting_agent="test-agent", project_id="acme-2026")

    events = fake_couchdb.find("audit_log", {"type": "audit_event"})["docs"]
    assert len(events) == 1
    assert events[0]["action"] == "mainframe_pull_element"


def test_real_tool_raises_not_implemented(fake_couchdb):
    request = MainframeFetchSourceRequest(
        tool="endevor",
        host="endevor-host",
        credential_ref="vault://mainframe/endevor/readonly",
        system="PAYSYS",
        subsystem="PAYROLL",
        element_type="COBOL",
        element_id="PAYROLL01",
    )
    with pytest.raises(NotImplementedError):
        mainframe_fetch_source(fake_couchdb, request, requesting_agent="test-agent", project_id="acme-2026")
