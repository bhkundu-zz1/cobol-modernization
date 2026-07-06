"""Tests the Codegen BFF's approval-gating join and generate/status proxy
routes, using httpx.MockTransport (no live services)."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

_RealAsyncClient = httpx.AsyncClient

EPICS = {"items": [{"_id": "epic-1", "title": "Payroll subsystem"}]}

STORIES_ONE_PROGRAM_APPROVED = {
    "items": [
        {
            "_id": "story-a",
            "epic_id": "epic-1",
            "title": "Extract PAYROLL01",
            "source_program_ids": ["PAYROLL01"],
            "code_generation_status": "not_generated",
        }
    ]
}

STORIES_MULTI_PROGRAM_MIXED = {
    "items": [
        {
            "_id": "story-mixed",
            "epic_id": "epic-1",
            "title": "Extract payroll + timesheet",
            "source_program_ids": ["PAYROLL01", "TIMESHEET"],
            "code_generation_status": "not_generated",
        }
    ]
}

STORIES_UNKNOWN_PROGRAM = {
    "items": [
        {
            "_id": "story-unknown",
            "epic_id": "epic-1",
            "title": "Extract UNKNOWN",
            "source_program_ids": ["UNKNOWN"],
            "code_generation_status": "not_generated",
        }
    ]
}

RECOMMENDATIONS_ONE_APPROVED = {
    "items": [
        {
            "_id": "rec-1",
            "program_id": "PAYROLL01",
            "recommended_target": "python_microservice",
            "human_review_status": "approved",
            "updated_at": "2026-07-05T00:00:00Z",
        }
    ]
}

RECOMMENDATIONS_MIXED_APPROVAL = {
    "items": [
        {
            "_id": "rec-1",
            "program_id": "PAYROLL01",
            "recommended_target": "python_microservice",
            "human_review_status": "approved",
            "updated_at": "2026-07-05T00:00:00Z",
        },
        {
            "_id": "rec-2",
            "program_id": "TIMESHEET",
            "recommended_target": "python_microservice",
            "human_review_status": "pending",
            "updated_at": "2026-07-05T00:00:00Z",
        },
    ]
}


def _transport(stories_payload: dict, recommendations_payload: dict) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/epics":
            return httpx.Response(200, json=EPICS)
        if path == "/epics/epic-1/stories":
            return httpx.Response(200, json=stories_payload)
        if path == "/recommendations":
            return httpx.Response(200, json=recommendations_payload)
        raise AssertionError(f"unexpected path: {path}")

    return httpx.MockTransport(handler)


@pytest.fixture
def client():
    return TestClient(app)


def _patch_client(monkeypatch, transport: httpx.MockTransport) -> None:
    def factory(**kwargs):
        kwargs.pop("transport", None)
        return _RealAsyncClient(transport=transport, **kwargs)

    monkeypatch.setattr("app.routes.codegen.httpx.AsyncClient", factory)


def test_eligible_stories_includes_fully_approved_story(client, monkeypatch):
    _patch_client(monkeypatch, _transport(STORIES_ONE_PROGRAM_APPROVED, RECOMMENDATIONS_ONE_APPROVED))

    response = client.get("/bff/codegen/eligible-stories", params={"project_id": "acme-2026"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["story"]["_id"] == "story-a"
    assert body["items"][0]["epic_title"] == "Payroll subsystem"
    assert body["items"][0]["recommended_targets"] == ["python_microservice"]


def test_eligible_stories_excludes_story_with_any_unapproved_program(client, monkeypatch):
    _patch_client(monkeypatch, _transport(STORIES_MULTI_PROGRAM_MIXED, RECOMMENDATIONS_MIXED_APPROVAL))

    response = client.get("/bff/codegen/eligible-stories", params={"project_id": "acme-2026"})

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_eligible_stories_excludes_story_with_no_matching_recommendation(client, monkeypatch):
    _patch_client(monkeypatch, _transport(STORIES_UNKNOWN_PROGRAM, RECOMMENDATIONS_ONE_APPROVED))

    response = client.get("/bff/codegen/eligible-stories", params={"project_id": "acme-2026"})

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_generate_proxies_to_job_pipeline_control_service(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/jobs/generate-code"
        return httpx.Response(202, json={"job_run_id": "jr-1", "status": "running"})

    transport = httpx.MockTransport(handler)
    _patch_client(monkeypatch, transport)

    response = client.post(
        "/bff/codegen/generate",
        json={"project_id": "acme-2026", "story_id": "story-a", "target_language": "python"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["job_run_id"] == "jr-1"
    assert body["status"] == "running"


def test_get_codegen_job_status_proxies_job_pipeline_control_service(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/jobs/jr-1"
        return httpx.Response(200, json={"job_run_id": "jr-1", "status": "completed", "tasks": []})

    transport = httpx.MockTransport(handler)
    _patch_client(monkeypatch, transport)

    response = client.get("/bff/codegen/jobs/jr-1", params={"project_id": "acme-2026"})

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
