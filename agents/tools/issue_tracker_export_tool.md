# MCP Tool: `issue_tracker.export`

Status: **REAL (GitHub) / documented-not-implemented (Jira)** — backs
`mcp_gateway/app/tools/export_tools.py`, per docs/architecture.md section 1b.

Exports selected `epic`/`story` documents to an external backlog tool.
`tool` selects the adapter implementation via the registry in
`agents/issue_tracker_export/adapter.py` (the Editor MFE's destination
picker sets this per export call, not an env-driven default like the
mainframe connector — a reviewer picks the destination interactively).

```
issue_tracker_export(
  tool: "github" | "jira",
  connection_config: dict,   # {"owner","repo","credential_ref"} for github;
                              # {"project_key","credential_ref"} for jira
  epic_ids: list[str],
  story_ids: list[str],
  requesting_agent: str,
  project_id: str,
) -> {
  "exported": [{"story_id": str, "external_issue_key": str, "external_issue_url": str}, ...],
  "failed": [{"story_id": str, "reason": str}, ...],
  "epic_milestones": [{"epic_id": str, "external_milestone_id": str, "external_milestone_url": str}, ...],
}
```

## This pass's actual coverage

`tool="github"` is fully implemented: one Milestone created per Epic (or
reused, matched by title, if a prior partial export already created it —
idempotent so retrying after a partial failure doesn't create duplicates),
one Issue created per Story assigned to that milestone, with acceptance
criteria and `source_program_ids` traceability written into the issue body
and a fixed migration-tracking label applied. See
`agents/issue_tracker_export/adapter.py`'s `GitHubAdapter` and
`docs/architecture.md` section 1b for the full design and endpoint list.

`tool="jira"` selects a real adapter class (`JiraAdapter`) whose methods
raise `NotImplementedError` naming "Jira Cloud REST API v3" as the missing
protocol — the Editor MFE's Jira connect form is real, but submitting an
export with Jira selected surfaces this error cleanly rather than silently
succeeding or falling back to GitHub. See `docs/deferred_scope.md`.

## Writeback and audit

- **`couchdb.write`-equivalent writeback**: each successfully exported story
  gets `export_status="exported"`, `export_target`, `external_issue_key`,
  `external_issue_url` written directly by this tool (not via a separate
  `couchdb.write` call — matches `mainframe_tools.py`'s pattern of writing
  through the gateway's own CouchDB client rather than round-tripping
  through another tool). Each epic with an exported story gets the
  equivalent `export_target`/`external_milestone_id`/`external_milestone_url`
  fields.
- **Audit**: one `audit.append` (`event_category="export"`,
  `action="issue_tracker_export_story"`) per successfully exported story,
  and one (`action="issue_tracker_export_milestone"`) per epic that got a
  milestone created/reused — a failed story is never written back or
  audited, only ever reported in the `failed` list.
- **Credentials**: `connection_config.credential_ref` is a reference
  (`env://VAR_NAME` this pass), never a literal secret — same rule as the
  mainframe connector.

## Why this replaced the earlier `jira.export`-only design

The original `jira_export_tool.md` declaration assumed Jira would be the
first (and initially only) export destination. Once GitHub was chosen as
the first *implemented* destination, the tool was generalized to a
`tool`-discriminated shape (matching `mainframe.fetch_source`'s own
`tool: Literal[...]` pattern) rather than shipping one tool per destination
— this keeps the Editor MFE's export call site identical regardless of
which destination a reviewer picks.
