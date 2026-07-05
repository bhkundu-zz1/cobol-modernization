"""issue_tracker.export — exports epic/story documents to GitHub or Jira
(docs/architecture.md section 1b).

Delegates to the adapter registry in agents/issue_tracker_export/adapter.py.
This module is intentionally thin: it validates the request, reads the
epic/story docs, resolves the adapter, calls it, writes back per-item
results, and logs audit events — it never constructs export data itself,
matching mainframe_tools.py's shape exactly.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

# agents/ lives as a sibling package to mcp_gateway/ in this monorepo; see
# mainframe_tools.py for the identical sys.path setup (the first consumer
# of this pattern) — reused here rather than duplicated logic diverging.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ..config import settings
from ..schemas import (
    AuditActor,
    AuditAppendRequest,
    ExportedMilestoneResult,
    ExportedStoryResult,
    FailedStoryResult,
    IssueTrackerExportRequest,
    IssueTrackerExportResult,
)
from .audit_tools import audit_append

if TYPE_CHECKING:
    from ..couchdb_client import CouchDBClient


def _fetch_docs(couchdb_client: "CouchDBClient", database: str, doc_ids: list[str]) -> list[dict[str, Any]]:
    docs = []
    for doc_id in doc_ids:
        doc = couchdb_client.get_document(database, doc_id)
        if doc is not None:
            docs.append(doc)
    return docs


def issue_tracker_export(
    couchdb_client: "CouchDBClient",
    request: IssueTrackerExportRequest,
    requesting_agent: str,
    project_id: str,
) -> IssueTrackerExportResult:
    from agents.issue_tracker_export.adapter import get_adapter  # noqa: PLC0415

    adapter = get_adapter(request.tool)

    epics = _fetch_docs(couchdb_client, settings.couchdb_db_backlog, request.epic_ids)
    stories = _fetch_docs(couchdb_client, settings.couchdb_db_backlog, request.story_ids)

    result = adapter.export_stories(connection_config=request.connection_config, epics=epics, stories=stories)

    exported_by_story_id = {item.story_id: item for item in result.exported}
    for story in stories:
        exported = exported_by_story_id.get(story["_id"])
        if exported is None:
            continue
        story["export_status"] = "exported"
        story["export_target"] = request.tool
        story["external_issue_key"] = exported.external_issue_key
        story["external_issue_url"] = exported.external_issue_url
        couchdb_client.put_document(settings.couchdb_db_backlog, story)

        audit_append(
            couchdb_client,
            AuditAppendRequest(
                project_id=project_id,
                event_category="export",
                actor=AuditActor(kind="agent", id=requesting_agent),
                action="issue_tracker_export_story",
                subject_doc_id=story["_id"],
                subject_doc_rev=story.get("_rev"),
                before_state_hash=None,
                after_state_hash=None,
                model_used=None,
                skill_version_hash=None,
            ),
        )

    milestones_by_epic_id = {m.epic_id: m for m in result.epic_milestones}
    for epic in epics:
        milestone = milestones_by_epic_id.get(epic["_id"])
        if milestone is None:
            continue
        epic["export_target"] = request.tool
        epic["external_milestone_id"] = milestone.external_milestone_id
        epic["external_milestone_url"] = milestone.external_milestone_url
        couchdb_client.put_document(settings.couchdb_db_backlog, epic)

        audit_append(
            couchdb_client,
            AuditAppendRequest(
                project_id=project_id,
                event_category="export",
                actor=AuditActor(kind="agent", id=requesting_agent),
                action="issue_tracker_export_milestone",
                subject_doc_id=epic["_id"],
                subject_doc_rev=epic.get("_rev"),
                before_state_hash=None,
                after_state_hash=None,
                model_used=None,
                skill_version_hash=None,
            ),
        )

    return IssueTrackerExportResult(
        exported=[
            ExportedStoryResult(
                story_id=item.story_id, external_issue_key=item.external_issue_key, external_issue_url=item.external_issue_url
            )
            for item in result.exported
        ],
        failed=[FailedStoryResult(story_id=item.story_id, reason=item.reason) for item in result.failed],
        epic_milestones=[
            ExportedMilestoneResult(
                epic_id=m.epic_id, external_milestone_id=m.external_milestone_id, external_milestone_url=m.external_milestone_url
            )
            for m in result.epic_milestones
        ],
    )
