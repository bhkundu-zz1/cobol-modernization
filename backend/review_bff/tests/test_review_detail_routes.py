"""Tests the Review BFF's per-row source/backlog lookups and the
generate-epics-stories proxy, using httpx.MockTransport (no live services)."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

_RealAsyncClient = httpx.AsyncClient


@pytest.fixture
def client():
    return TestClient(app)


def _mock_client(monkeypatch, handler):
    transport = httpx.MockTransport(handler)

    def factory(**kwargs):
        kwargs.pop("transport", None)
        return _RealAsyncClient(transport=transport, **kwargs)

    monkeypatch.setattr("app.routes.review_items.httpx.AsyncClient", factory)


def test_get_source_returns_source_text_and_relative_path(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/recommendations/rec-1":
            return httpx.Response(200, json={"source_file_id": "sf-1"})
        if request.url.path == "/source-files/sf-1":
            return httpx.Response(
                200,
                json={
                    "filename": "PAYROLL01.CBL",
                    "source_text": "IDENTIFICATION DIVISION.",
                    "relative_path": "payroll-project/PAYROLL01.CBL",
                    "language": "cobol",
                },
            )
        raise AssertionError(f"unexpected path: {request.url.path}")

    _mock_client(monkeypatch, handler)
    response = client.get("/bff/review-items/rec-1/source", params={"project_id": "acme-2026"})
    assert response.status_code == 200
    body = response.json()
    assert body["source_text"] == "IDENTIFICATION DIVISION."
    assert body["relative_path"] == "payroll-project/PAYROLL01.CBL"


def test_get_source_returns_nulls_when_recommendation_has_no_source_file_id(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"source_file_id": None})

    _mock_client(monkeypatch, handler)
    response = client.get("/bff/review-items/rec-1/source", params={"project_id": "acme-2026"})
    assert response.status_code == 200
    body = response.json()
    assert body["source_text"] is None
    assert body["filename"] is None


def test_get_backlog_returns_matching_epic_and_story(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/recommendations/rec-1":
            return httpx.Response(200, json={"program_id": "PAYROLL01"})
        if request.url.path == "/epics":
            return httpx.Response(200, json={"items": [{"_id": "epic-1", "title": "Payroll subsystem"}]})
        if request.url.path == "/epics/epic-1/stories":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "_id": "story-1",
                            "epic_id": "epic-1",
                            "title": "Extract PAYROLL01",
                            "source_program_ids": ["PAYROLL01"],
                            "confidence_score": 0.85,
                        }
                    ]
                },
            )
        raise AssertionError(f"unexpected path: {request.url.path}")

    _mock_client(monkeypatch, handler)
    response = client.get("/bff/review-items/rec-1/backlog", params={"project_id": "acme-2026"})
    assert response.status_code == 200
    body = response.json()
    assert body["epic"]["title"] == "Payroll subsystem"
    assert body["story"]["title"] == "Extract PAYROLL01"


def test_get_backlog_returns_nulls_when_program_not_yet_grouped(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/recommendations/rec-1":
            return httpx.Response(200, json={"program_id": "PAYROLL01"})
        if request.url.path == "/epics":
            return httpx.Response(200, json={"items": []})
        raise AssertionError(f"unexpected path: {request.url.path}")

    _mock_client(monkeypatch, handler)
    response = client.get("/bff/review-items/rec-1/backlog", params={"project_id": "acme-2026"})
    assert response.status_code == 200
    body = response.json()
    assert body["epic"] is None
    assert body["story"] is None


def test_generate_epics_stories_proxies_to_job_pipeline_control_service(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/jobs/generate-epics-stories"
        return httpx.Response(202, json={"job_run_id": "jr-epic-1", "status": "running"})

    _mock_client(monkeypatch, handler)
    response = client.post("/bff/generate-epics-stories", json={"project_id": "acme-2026"})
    assert response.status_code == 202
    assert response.json()["job_run_id"] == "jr-epic-1"


def test_get_job_status_proxies_to_job_pipeline_control_service(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/jobs/jr-epic-1"
        return httpx.Response(200, json={"job_run_id": "jr-epic-1", "status": "completed", "tasks": []})

    _mock_client(monkeypatch, handler)
    response = client.get("/bff/jobs/jr-epic-1", params={"project_id": "acme-2026"})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_get_job_status_propagates_404(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text='{"detail": "job_run not found"}')

    _mock_client(monkeypatch, handler)
    response = client.get("/bff/jobs/jr-missing", params={"project_id": "acme-2026"})
    assert response.status_code == 404
