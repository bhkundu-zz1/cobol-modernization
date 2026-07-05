"""Tests for the issue_tracker.export MCP tool — validate-delegate-writeback-
audit flow, with the adapter registry mocked (adapter HTTP behavior itself
is covered by agents/tests/test_issue_tracker_adapter.py)."""

from unittest.mock import patch

from app.schemas import IssueTrackerExportRequest
from app.tools.export_tools import issue_tracker_export


class _FakeAdapter:
    def __init__(self, export_result):
        self._export_result = export_result

    def export_stories(self, *, connection_config, epics, stories):
        return self._export_result


def _seed_epic_and_story(fake_couchdb):
    epic_result = fake_couchdb.put_document(
        "backlog", {"type": "epic", "title": "Extract payroll", "description": "..."}
    )
    story_result = fake_couchdb.put_document(
        "backlog",
        {
            "type": "story",
            "epic_id": epic_result["id"],
            "title": "Extract gross-pay calc",
            "description": "...",
            "generated_by_agent": "epic-story-writer@v1",
            "export_status": "not_exported",
        },
    )
    return epic_result["id"], story_result["id"]


def test_successful_export_writes_back_story_and_epic_and_audits(fake_couchdb):
    from agents.issue_tracker_export.adapter import ExportedItem, ExportedMilestone, ExportResult

    epic_id, story_id = _seed_epic_and_story(fake_couchdb)

    fake_result = ExportResult(
        exported=[ExportedItem(story_id=story_id, external_issue_key="acme/repo#42", external_issue_url="https://github.com/acme/repo/issues/42")],
        failed=[],
        epic_milestones=[ExportedMilestone(epic_id=epic_id, external_milestone_id="7", external_milestone_url="https://github.com/acme/repo/milestone/7")],
    )

    with patch("agents.issue_tracker_export.adapter.get_adapter", return_value=_FakeAdapter(fake_result)):
        result = issue_tracker_export(
            fake_couchdb,
            IssueTrackerExportRequest(
                tool="github",
                connection_config={"owner": "acme", "repo": "repo", "credential_ref": "env://X"},
                epic_ids=[epic_id],
                story_ids=[story_id],
            ),
            requesting_agent="test-agent",
            project_id="acme-2026",
        )

    assert len(result.exported) == 1
    assert result.exported[0].external_issue_key == "acme/repo#42"
    assert len(result.epic_milestones) == 1

    story_doc = fake_couchdb.get_document("backlog", story_id)
    assert story_doc["export_status"] == "exported"
    assert story_doc["export_target"] == "github"
    assert story_doc["external_issue_url"] == "https://github.com/acme/repo/issues/42"

    epic_doc = fake_couchdb.get_document("backlog", epic_id)
    assert epic_doc["export_target"] == "github"
    assert epic_doc["external_milestone_id"] == "7"

    audit_events = fake_couchdb.find("audit_log", {"type": "audit_event", "event_category": "export"})["docs"]
    actions = {e["action"] for e in audit_events}
    assert "issue_tracker_export_story" in actions
    assert "issue_tracker_export_milestone" in actions


def test_failed_export_does_not_write_back_or_audit_that_story(fake_couchdb):
    from agents.issue_tracker_export.adapter import ExportResult, FailedItem

    epic_id, story_id = _seed_epic_and_story(fake_couchdb)

    fake_result = ExportResult(exported=[], failed=[FailedItem(story_id=story_id, reason="rate limited")], epic_milestones=[])

    with patch("agents.issue_tracker_export.adapter.get_adapter", return_value=_FakeAdapter(fake_result)):
        result = issue_tracker_export(
            fake_couchdb,
            IssueTrackerExportRequest(
                tool="github",
                connection_config={"owner": "acme", "repo": "repo", "credential_ref": "env://X"},
                epic_ids=[epic_id],
                story_ids=[story_id],
            ),
            requesting_agent="test-agent",
            project_id="acme-2026",
        )

    assert result.exported == []
    assert len(result.failed) == 1
    assert result.failed[0].reason == "rate limited"

    story_doc = fake_couchdb.get_document("backlog", story_id)
    assert story_doc["export_status"] == "not_exported"

    audit_events = fake_couchdb.find("audit_log", {"type": "audit_event", "event_category": "export"})["docs"]
    assert audit_events == []
