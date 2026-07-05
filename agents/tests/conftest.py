"""Test doubles for MCPClient and LLMClient, used across agents/tests/*."""

import uuid
from typing import Any, Callable

import pytest


def _matches_selector(doc: dict, selector: dict) -> bool:
    return all(doc.get(key) == value for key, value in selector.items())


class FakeMCPClient:
    """In-memory stand-in for agents.common.mcp_client.MCPClient."""

    def __init__(self) -> None:
        self.databases: dict[str, dict[str, dict[str, Any]]] = {}
        self.audit_events: list[dict[str, Any]] = []
        self.killed = False

    def couchdb_write(self, database: str, doc: dict, project_id: str, created_by: str, trace_id: str) -> dict:
        db = self.databases.setdefault(database, {})
        doc = dict(doc)
        doc_id = doc.get("_id") or str(uuid.uuid4())
        doc["_id"] = doc_id
        doc["project_id"] = project_id
        doc["created_by"] = created_by
        doc["trace_id"] = trace_id
        db[doc_id] = doc
        return {"id": doc_id, "rev": "1-fake"}

    def couchdb_read(self, database: str, doc_id: str | None = None, mango_selector: dict | None = None, limit: int = 50) -> dict:
        db = self.databases.get(database, {})
        if doc_id is not None:
            doc = db.get(doc_id)
            return {"docs": [doc] if doc else [], "bookmark": None}
        docs = [d for d in db.values() if _matches_selector(d, mango_selector or {})]
        return {"docs": docs[:limit], "bookmark": None}

    def audit_append(self, **kwargs: Any) -> dict:
        self.audit_events.append(kwargs)
        return {"id": str(uuid.uuid4()), "rev": "1-fake", "this_event_hash": "fakehash"}

    def kill_check(self, project_id: str, job_run_id: str) -> dict:
        return {"killed": self.killed, "reason": "test-forced-kill" if self.killed else None}

    def kill_set(self, scope: str, requested_by: str, scope_id: str | None = None) -> dict:
        self.killed = True
        self.audit_events.append(
            {"event_category": "kill_switch", "action": f"kill_set(scope={scope}, scope_id={scope_id})"}
        )
        return {"ok": True}

    def mainframe_fetch_source(
        self,
        tool: str,
        host: str,
        credential_ref: str,
        system: str,
        subsystem: str,
        element_type: str,
        requesting_agent: str,
        project_id: str,
        element_id: str | None = None,
    ) -> dict:
        """Delegates to the real adapter registry so tests exercise the same
        mock-runs / real-tools-raise-NotImplementedError behavior as
        production code, rather than re-mocking it here."""
        from agents.mainframe_ingestion.adapter import get_adapter

        adapter = get_adapter(tool)
        if element_id is None:
            elements = adapter.list_elements(
                host=host, credential_ref=credential_ref, system=system, subsystem=subsystem, element_type=element_type
            )
            return {"elements": elements}
        source_text = adapter.get_source(
            host=host, credential_ref=credential_ref, system=system, subsystem=subsystem, element_type=element_type, element_id=element_id
        )
        metadata = adapter.get_metadata(
            host=host, credential_ref=credential_ref, system=system, subsystem=subsystem, element_type=element_type, element_id=element_id
        )
        return {"source_text": source_text, "metadata": metadata}

    def issue_tracker_export(
        self,
        tool: str,
        connection_config: dict[str, Any],
        epic_ids: list[str],
        story_ids: list[str],
        requesting_agent: str,
        project_id: str,
    ) -> dict:
        """Delegates to the real adapter registry (same rationale as
        mainframe_fetch_source above) — a caller can seed epic/story docs
        into this fake's own `backlog` database and get real
        GitHub-mocked-HTTP / Jira-NotImplementedError behavior without
        re-mocking export logic here. Note: this fake does NOT make real
        HTTP calls itself — callers using tool="github" against this fake
        still need to patch agents.issue_tracker_export.adapter.httpx.Client
        the same way agents/tests/test_issue_tracker_adapter.py does, or
        pass tool="jira" to exercise the NotImplementedError path with no
        network involved at all.
        """
        from agents.issue_tracker_export.adapter import get_adapter

        adapter = get_adapter(tool)
        backlog = self.databases.get("backlog", {})
        epics = [backlog[doc_id] for doc_id in epic_ids if doc_id in backlog]
        stories = [backlog[doc_id] for doc_id in story_ids if doc_id in backlog]

        result = adapter.export_stories(connection_config=connection_config, epics=epics, stories=stories)

        exported_by_story_id = {item.story_id: item for item in result.exported}
        for story in stories:
            exported = exported_by_story_id.get(story["_id"])
            if exported is None:
                continue
            story["export_status"] = "exported"
            story["export_target"] = tool
            story["external_issue_key"] = exported.external_issue_key
            story["external_issue_url"] = exported.external_issue_url
            self.audit_events.append({"event_category": "export", "action": "issue_tracker_export_story"})

        milestones_by_epic_id = {m.epic_id: m for m in result.epic_milestones}
        for epic in epics:
            milestone = milestones_by_epic_id.get(epic["_id"])
            if milestone is None:
                continue
            epic["export_target"] = tool
            epic["external_milestone_id"] = milestone.external_milestone_id
            epic["external_milestone_url"] = milestone.external_milestone_url
            self.audit_events.append({"event_category": "export", "action": "issue_tracker_export_milestone"})

        return {
            "exported": [
                {"story_id": i.story_id, "external_issue_key": i.external_issue_key, "external_issue_url": i.external_issue_url}
                for i in result.exported
            ],
            "failed": [{"story_id": i.story_id, "reason": i.reason} for i in result.failed],
            "epic_milestones": [
                {"epic_id": m.epic_id, "external_milestone_id": m.external_milestone_id, "external_milestone_url": m.external_milestone_url}
                for m in result.epic_milestones
            ],
        }


class FakeLLMClient:
    """Returns pre-programmed JSON responses in call order, matching the
    plan's 'LLM/MCP test-doubled' testing approach."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = list(responses)
        self.calls: list[str] = []

    def complete_json(self, model: str, prompt: str, *, project_id: str, job_run_id: str) -> dict:
        self.calls.append(prompt)
        if not self._responses:
            raise AssertionError("FakeLLMClient ran out of programmed responses")
        return self._responses.pop(0)


@pytest.fixture
def fake_mcp_client() -> FakeMCPClient:
    return FakeMCPClient()


@pytest.fixture
def make_fake_llm_client() -> Callable[[list[dict]], FakeLLMClient]:
    return FakeLLMClient
