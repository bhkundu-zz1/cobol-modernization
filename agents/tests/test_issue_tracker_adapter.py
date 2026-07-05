"""Tests for the issue-tracker export adapter registry (docs/architecture.md
section 1b). Uses httpx.MockTransport (not respx — confirmed unavailable in
this environment) to fake GitHub's REST endpoints."""

import os

import httpx
import pytest

from agents.issue_tracker_export.adapter import GitHubAdapter, JiraAdapter, get_adapter

EPIC = {"_id": "epic-1", "title": "Extract payroll gross-pay calc", "description": "Payroll subsystem cluster"}
STORY = {
    "_id": "story-1",
    "epic_id": "epic-1",
    "title": "Extract gross-pay calculation into Python microservice",
    "description": "Move 2000-CALC-GROSS into a standalone service.",
    "acceptance_criteria": ["Handles overtime correctly", "Matches existing rounding behavior"],
    "source_program_ids": ["PAYROLL01:1000-MAIN", "PAYROLL01:2000-CALC-GROSS"],
}

CONNECTION_CONFIG = {"owner": "acme-org", "repo": "payroll-modernization", "credential_ref": "env://TEST_GITHUB_PAT"}


@pytest.fixture(autouse=True)
def github_pat_env(monkeypatch):
    monkeypatch.setenv("TEST_GITHUB_PAT", "ghp_faketoken")


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def _patched_client(monkeypatch, transport):
    real_client = httpx.Client

    def factory(**kwargs):
        kwargs["transport"] = transport
        return real_client(**kwargs)

    monkeypatch.setattr("agents.issue_tracker_export.adapter.httpx.Client", factory)


def test_get_adapter_returns_github_adapter():
    adapter = get_adapter("github")
    assert isinstance(adapter, GitHubAdapter)


def test_get_adapter_returns_jira_adapter():
    adapter = get_adapter("jira")
    assert isinstance(adapter, JiraAdapter)


def test_unknown_tool_raises_value_error():
    with pytest.raises(ValueError):
        get_adapter("some-unsupported-tracker")


def test_jira_adapter_raises_not_implemented_for_every_method():
    adapter = get_adapter("jira")
    with pytest.raises(NotImplementedError):
        adapter.validate_connection(connection_config={})
    with pytest.raises(NotImplementedError):
        adapter.list_repos_or_projects(connection_config={})
    with pytest.raises(NotImplementedError):
        adapter.export_stories(connection_config={}, epics=[], stories=[])


def test_resolve_credential_missing_env_var_raises(monkeypatch):
    monkeypatch.delenv("TEST_MISSING_VAR", raising=False)
    from agents.issue_tracker_export.adapter import _resolve_credential

    with pytest.raises(ValueError, match="did not resolve"):
        _resolve_credential("env://TEST_MISSING_VAR")


def test_resolve_credential_bad_scheme_raises():
    from agents.issue_tracker_export.adapter import _resolve_credential

    with pytest.raises(ValueError, match="unsupported credential_ref scheme"):
        _resolve_credential("literal-secret-not-a-reference")


def test_validate_connection_success(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/acme-org/payroll-modernization"
        assert request.headers["authorization"] == "Bearer ghp_faketoken"
        return httpx.Response(200, json={"full_name": "acme-org/payroll-modernization"})

    _patched_client(monkeypatch, _mock_transport(handler))
    GitHubAdapter().validate_connection(connection_config=CONNECTION_CONFIG)


def test_validate_connection_404_raises_clear_error(monkeypatch):
    _patched_client(monkeypatch, _mock_transport(lambda request: httpx.Response(404)))
    with pytest.raises(ValueError, match="not found"):
        GitHubAdapter().validate_connection(connection_config=CONNECTION_CONFIG)


def test_validate_connection_401_raises_clear_error(monkeypatch):
    _patched_client(monkeypatch, _mock_transport(lambda request: httpx.Response(401)))
    with pytest.raises(ValueError, match="invalid or expired token"):
        GitHubAdapter().validate_connection(connection_config=CONNECTION_CONFIG)


def test_export_stories_creates_milestone_and_issue(monkeypatch):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/labels") and request.method == "GET":
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/labels") and request.method == "POST":
            return httpx.Response(201, json={"name": "migration-backlog"})
        if request.url.path.endswith("/milestones") and request.method == "GET":
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/milestones") and request.method == "POST":
            return httpx.Response(
                201, json={"number": 7, "html_url": "https://github.com/acme-org/payroll-modernization/milestone/7"}
            )
        if request.url.path.endswith("/issues") and request.method == "POST":
            body = httpx.Request("POST", request.url, content=request.content).content
            return httpx.Response(
                201,
                json={
                    "number": 42,
                    "html_url": "https://github.com/acme-org/payroll-modernization/issues/42",
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    _patched_client(monkeypatch, _mock_transport(handler))

    result = GitHubAdapter().export_stories(connection_config=CONNECTION_CONFIG, epics=[EPIC], stories=[STORY])

    assert len(result.exported) == 1
    assert result.exported[0].story_id == "story-1"
    assert result.exported[0].external_issue_key == "acme-org/payroll-modernization#42"
    assert result.exported[0].external_issue_url.endswith("/issues/42")

    assert len(result.epic_milestones) == 1
    assert result.epic_milestones[0].epic_id == "epic-1"
    assert result.epic_milestones[0].external_milestone_id == "7"

    assert result.failed == []


def test_export_stories_reuses_existing_milestone(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/labels"):
            return httpx.Response(200, json=[{"name": "migration-backlog"}]) if request.method == "GET" else httpx.Response(201)
        if request.url.path.endswith("/milestones") and request.method == "GET":
            return httpx.Response(
                200,
                json=[{"number": 3, "title": "Extract payroll gross-pay calc", "html_url": "https://github.com/x/y/milestone/3"}],
            )
        if request.url.path.endswith("/issues") and request.method == "POST":
            return httpx.Response(201, json={"number": 10, "html_url": "https://github.com/x/y/issues/10"})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}, should not create a new milestone")

    _patched_client(monkeypatch, _mock_transport(handler))

    result = GitHubAdapter().export_stories(connection_config=CONNECTION_CONFIG, epics=[EPIC], stories=[STORY])

    assert result.epic_milestones[0].external_milestone_id == "3"


def test_export_stories_one_failure_does_not_abort_batch(monkeypatch):
    story_2 = {**STORY, "_id": "story-2", "title": "Second story"}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/labels"):
            return httpx.Response(200, json=[{"name": "migration-backlog"}]) if request.method == "GET" else httpx.Response(201)
        if request.url.path.endswith("/milestones") and request.method == "GET":
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/milestones") and request.method == "POST":
            return httpx.Response(201, json={"number": 1, "html_url": "https://github.com/x/y/milestone/1"})
        if request.url.path.endswith("/issues") and request.method == "POST":
            body = request.content.decode()
            if "Second story" in body:
                return httpx.Response(500, text="internal server error")
            return httpx.Response(201, json={"number": 5, "html_url": "https://github.com/x/y/issues/5"})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    _patched_client(monkeypatch, _mock_transport(handler))

    result = GitHubAdapter().export_stories(connection_config=CONNECTION_CONFIG, epics=[EPIC], stories=[STORY, story_2])

    assert len(result.exported) == 1
    assert len(result.failed) == 1
    assert result.failed[0].story_id == "story-2"


def test_export_stories_rate_limit_routes_to_failed(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/labels"):
            return httpx.Response(200, json=[{"name": "migration-backlog"}]) if request.method == "GET" else httpx.Response(201)
        if request.url.path.endswith("/milestones") and request.method == "GET":
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/milestones") and request.method == "POST":
            return httpx.Response(201, json={"number": 1, "html_url": "https://github.com/x/y/milestone/1"})
        if request.url.path.endswith("/issues") and request.method == "POST":
            return httpx.Response(403, json={"message": "rate limit exceeded"})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    _patched_client(monkeypatch, _mock_transport(handler))

    result = GitHubAdapter().export_stories(connection_config=CONNECTION_CONFIG, epics=[EPIC], stories=[STORY])

    assert result.exported == []
    assert len(result.failed) == 1
    assert "rate limit" in result.failed[0].reason.lower()
