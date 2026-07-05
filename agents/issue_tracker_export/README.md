# Issue Tracker Export Adapter

Real adapter-registry pattern for exporting `epic`/`story` documents to an
external backlog tool (docs/architecture.md section 1b) — the export-side
mirror of `agents/mainframe_ingestion/`'s ingestion-side connector.

## Status

**GitHub is real and fully implemented.** `GitHubAdapter` creates one
Milestone per Epic and one Issue per Story (assigned to that milestone),
using GitHub's plain REST Issues API (not the Projects v2 GraphQL API).

**Jira is a real class, not implemented.** `JiraAdapter` implements the same
interface but every method raises `NotImplementedError` naming the missing
protocol ("Jira Cloud REST API v3") — the UI surface (a connect form) is
real; the wire protocol is future work. See `docs/deferred_scope.md`.

## Interface

```
class IssueTrackerAdapter(ABC):
    def validate_connection(self, *, connection_config: dict) -> None: ...
    def list_repos_or_projects(self, *, connection_config: dict) -> list[dict]: ...
    def export_stories(self, *, connection_config, epics, stories) -> ExportResult: ...
```

`get_adapter(tool)` (`tool` is `"github"` or `"jira"`) is the single seam
`mcp_gateway/app/tools/export_tools.py` depends on — selecting a tool is a
runtime choice (the Editor MFE's destination picker), not a code change.

## Credentials

`connection_config["credential_ref"]` is a reference, never a literal
secret — `env://VAR_NAME` resolves to `os.environ["VAR_NAME"]` this pass
(a placeholder for a real secrets-manager integration later), matching the
mainframe connector's "reference not literal" rule. `GitHubAdapter` is the
first adapter in this repo that actually dereferences a credential into a
live token, since it's the first adapter that makes a real outbound call.

## Why GitHub Issues REST, not Projects v2

Milestones are a first-class, stable GitHub concept that maps 1:1 onto
"Epic" without needing Projects v2's newer, more complex data model or its
GraphQL-only API surface and separate auth scopes. See
`docs/architecture.md` section 1b for the full rationale.
