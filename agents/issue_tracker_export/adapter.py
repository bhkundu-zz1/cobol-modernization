"""Issue-tracker export adapter interface + registry (docs/architecture.md section 1b).

`get_adapter(tool)` is the single seam export_tools.py depends on — mirrors
agents/mainframe_ingestion/adapter.py's structure exactly. Selecting Jira
returns a real adapter class whose methods raise NotImplementedError naming
the missing protocol, never a silent mock fallback. GitHubAdapter is the
first adapter in this repo that makes real outbound HTTP calls using a
resolved credential (every mainframe adapter is either mock or
not-implemented, so none of them ever needed to actually dereference a
credential_ref into a usable secret).
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

GITHUB_API_BASE = "https://api.github.com"
MIGRATION_LABELS = ["migration-backlog"]


@dataclass
class ExportedItem:
    story_id: str
    external_issue_key: str
    external_issue_url: str


@dataclass
class FailedItem:
    story_id: str
    reason: str


@dataclass
class ExportedMilestone:
    epic_id: str
    external_milestone_id: str
    external_milestone_url: str


@dataclass
class ExportResult:
    exported: list[ExportedItem] = field(default_factory=list)
    failed: list[FailedItem] = field(default_factory=list)
    epic_milestones: list[ExportedMilestone] = field(default_factory=list)


class IssueTrackerAdapter(ABC):
    """Common interface every issue-tracker adapter implements (docs/architecture.md section 1b)."""

    @abstractmethod
    def validate_connection(self, *, connection_config: dict[str, Any]) -> None: ...

    @abstractmethod
    def list_repos_or_projects(self, *, connection_config: dict[str, Any]) -> list[dict[str, Any]]: ...

    @abstractmethod
    def export_stories(
        self, *, connection_config: dict[str, Any], epics: list[dict[str, Any]], stories: list[dict[str, Any]]
    ) -> ExportResult: ...


def _resolve_credential(credential_ref: str) -> str:
    """Resolves a credential_ref into a usable secret. Convention this pass:
    `env://VAR_NAME` reads `os.environ["VAR_NAME"]`. This is a placeholder
    for a real secrets-manager/Vault integration (future work) — the point
    right now is that credential_ref is a reference, never a literal secret,
    matching the mainframe connector's rule (architecture.md section 1a),
    even though the mainframe adapters never actually had to dereference one
    since none of them make a real HTTP call yet.
    """
    if not credential_ref.startswith("env://"):
        raise ValueError(f"unsupported credential_ref scheme: {credential_ref!r}; expected 'env://VAR_NAME'")
    var_name = credential_ref.removeprefix("env://")
    value = os.environ.get(var_name)
    if not value:
        raise ValueError(f"credential_ref {credential_ref!r} did not resolve: {var_name} is not set")
    return value


class GitHubAdapter(IssueTrackerAdapter):
    """The only adapter with a real, runnable implementation this pass.
    connection_config shape: {"owner": str, "repo": str, "credential_ref": str}.
    """

    def _client(self, connection_config: dict[str, Any]) -> httpx.Client:
        token = _resolve_credential(connection_config["credential_ref"])
        return httpx.Client(
            base_url=GITHUB_API_BASE,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    def validate_connection(self, *, connection_config: dict[str, Any]) -> None:
        owner, repo = connection_config["owner"], connection_config["repo"]
        with self._client(connection_config) as client:
            response = client.get(f"/repos/{owner}/{repo}")
        if response.status_code == 404:
            raise ValueError(f"GitHub repo {owner}/{repo} not found or not accessible with this token")
        if response.status_code == 401:
            raise ValueError("GitHub credential_ref resolved to an invalid or expired token")
        response.raise_for_status()

    def list_repos_or_projects(self, *, connection_config: dict[str, Any]) -> list[dict[str, Any]]:
        with self._client(connection_config) as client:
            response = client.get("/user/repos")
        response.raise_for_status()
        return [{"id": r["id"], "name": r["full_name"]} for r in response.json()]

    def _find_or_create_milestone(self, client: httpx.Client, owner: str, repo: str, epic: dict[str, Any]) -> dict[str, Any]:
        existing_response = client.get(f"/repos/{owner}/{repo}/milestones", params={"state": "all"})
        existing_response.raise_for_status()
        for milestone in existing_response.json():
            if milestone["title"] == epic["title"]:
                return milestone

        create_response = client.post(
            f"/repos/{owner}/{repo}/milestones",
            json={"title": epic["title"], "description": epic.get("description", ""), "state": "open"},
        )
        create_response.raise_for_status()
        return create_response.json()

    def _ensure_labels_exist(self, client: httpx.Client, owner: str, repo: str, labels: list[str]) -> None:
        existing_response = client.get(f"/repos/{owner}/{repo}/labels", params={"per_page": 100})
        existing_response.raise_for_status()
        existing_names = {label["name"] for label in existing_response.json()}
        for label in labels:
            if label not in existing_names:
                # A 422 here (e.g. a race with another export) is not fatal —
                # the label existing is what we actually need, regardless of
                # who created it.
                client.post(f"/repos/{owner}/{repo}/labels", json={"name": label})

    def _build_issue_body(self, story: dict[str, Any]) -> str:
        lines = [story.get("description", ""), ""]
        acceptance_criteria = story.get("acceptance_criteria", [])
        if acceptance_criteria:
            lines.append("## Acceptance Criteria")
            lines.extend(f"- {criterion}" for criterion in acceptance_criteria)
            lines.append("")
        source_program_ids = story.get("source_program_ids", [])
        if source_program_ids:
            lines.append("## Traceability")
            lines.extend(f"- `{program_id}`" for program_id in source_program_ids)
        return "\n".join(lines)

    def export_stories(
        self, *, connection_config: dict[str, Any], epics: list[dict[str, Any]], stories: list[dict[str, Any]]
    ) -> ExportResult:
        owner, repo = connection_config["owner"], connection_config["repo"]
        result = ExportResult()

        stories_by_epic_id: dict[str, list[dict[str, Any]]] = {}
        for story in stories:
            stories_by_epic_id.setdefault(story["epic_id"], []).append(story)

        with self._client(connection_config) as client:
            self._ensure_labels_exist(client, owner, repo, MIGRATION_LABELS)

            for epic in epics:
                epic_stories = stories_by_epic_id.get(epic["_id"], [])
                if not epic_stories:
                    continue

                try:
                    milestone = self._find_or_create_milestone(client, owner, repo, epic)
                except httpx.HTTPStatusError as exc:
                    for story in epic_stories:
                        result.failed.append(FailedItem(story_id=story["_id"], reason=f"milestone creation failed: {exc}"))
                    continue

                result.epic_milestones.append(
                    ExportedMilestone(
                        epic_id=epic["_id"],
                        external_milestone_id=str(milestone["number"]),
                        external_milestone_url=milestone["html_url"],
                    )
                )

                for story in epic_stories:
                    try:
                        response = client.post(
                            f"/repos/{owner}/{repo}/issues",
                            json={
                                "title": story["title"],
                                "body": self._build_issue_body(story),
                                "milestone": milestone["number"],
                                "labels": MIGRATION_LABELS,
                            },
                        )
                        if response.status_code in (403, 429):
                            result.failed.append(
                                FailedItem(story_id=story["_id"], reason="GitHub rate limit hit; retry later")
                            )
                            continue
                        response.raise_for_status()
                        issue = response.json()
                        result.exported.append(
                            ExportedItem(
                                story_id=story["_id"],
                                external_issue_key=f"{owner}/{repo}#{issue['number']}",
                                external_issue_url=issue["html_url"],
                            )
                        )
                    except httpx.HTTPStatusError as exc:
                        result.failed.append(FailedItem(story_id=story["_id"], reason=str(exc)))

        return result


class _NotYetImplementedAdapter(IssueTrackerAdapter):
    """Base for real (non-GitHub) adapters: real class, real interface, but
    every method fails loudly rather than silently returning mock data —
    mirrors agents/mainframe_ingestion/adapter.py's _NotYetImplementedAdapter."""

    tool_name: str
    protocol_description: str

    def _not_implemented(self) -> NotImplementedError:
        return NotImplementedError(
            f"{self.tool_name} connector not yet implemented ({self.protocol_description}); "
            f"only GitHub export is available this pass. See docs/deferred_scope.md."
        )

    def validate_connection(self, *, connection_config: dict[str, Any]) -> None:
        raise self._not_implemented()

    def list_repos_or_projects(self, *, connection_config: dict[str, Any]) -> list[dict[str, Any]]:
        raise self._not_implemented()

    def export_stories(
        self, *, connection_config: dict[str, Any], epics: list[dict[str, Any]], stories: list[dict[str, Any]]
    ) -> ExportResult:
        raise self._not_implemented()


class JiraAdapter(_NotYetImplementedAdapter):
    tool_name = "Jira"
    protocol_description = "Jira Cloud REST API v3 (issue + project auth)"


_ADAPTERS: dict[str, type[IssueTrackerAdapter]] = {
    "github": GitHubAdapter,
    "jira": JiraAdapter,
}


def get_adapter(tool: str) -> IssueTrackerAdapter:
    try:
        adapter_cls = _ADAPTERS[tool]
    except KeyError:
        raise ValueError(f"unknown issue tracker tool: {tool!r}; expected one of {sorted(_ADAPTERS)}") from None
    return adapter_cls()
