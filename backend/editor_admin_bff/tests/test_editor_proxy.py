"""Tests the Editor/Admin BFF's proxy routes to epic_story_service, using
httpx.MockTransport (no live service), mirroring review_bff's test convention."""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

_RealAsyncClient = httpx.AsyncClient


def _mock_client(monkeypatch, handler):
    transport = httpx.MockTransport(handler)

    def factory(**kwargs):
        kwargs.pop("transport", None)
        return _RealAsyncClient(transport=transport, **kwargs)

    monkeypatch.setattr("app.routes.editor_items.httpx.AsyncClient", factory)


@pytest.fixture
def client():
    return TestClient(app)


def test_list_epics_proxies_to_epic_story_service(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/epics"
        assert request.url.params["project_id"] == "acme-2026"
        return httpx.Response(200, json={"items": [{"_id": "epic-1"}], "bookmark": None})

    _mock_client(monkeypatch, handler)
    response = client.get("/bff/epics", params={"project_id": "acme-2026"})
    assert response.status_code == 200
    assert response.json()["items"] == [{"_id": "epic-1"}]


def test_list_epic_stories_proxies_to_epic_story_service(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/epics/epic-1/stories"
        return httpx.Response(200, json={"items": [{"_id": "story-1"}], "bookmark": None})

    _mock_client(monkeypatch, handler)
    response = client.get("/bff/epics/epic-1/stories", params={"project_id": "acme-2026"})
    assert response.status_code == 200
    assert response.json()["items"] == [{"_id": "story-1"}]


def test_update_story_proxies_and_returns_result(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/stories/story-1"
        assert request.method == "PATCH"
        return httpx.Response(200, json={"story_id": "story-1", "edited_by_human": True, "edit_history_ref": ["e1"]})

    _mock_client(monkeypatch, handler)
    response = client.patch(
        "/bff/stories/story-1", json={"title": "Revised title", "edited_by": "bhakti.kundu@gmail.com"}
    )
    assert response.status_code == 200
    assert response.json()["edited_by_human"] is True


def test_update_story_propagates_upstream_error_status(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="story not found")

    _mock_client(monkeypatch, handler)
    response = client.patch("/bff/stories/nonexistent", json={"edited_by": "x@example.com"})
    assert response.status_code == 404


def test_export_proxies_and_propagates_501_for_jira(client, monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/export"
        return httpx.Response(501, text="Jira export is not yet implemented")

    _mock_client(monkeypatch, handler)
    response = client.post(
        "/bff/export",
        json={
            "project_id": "acme-2026",
            "tool": "jira",
            "connection_config": {"project_key": "PROJ", "credential_ref": "env://X"},
            "epic_ids": ["epic-1"],
            "story_ids": ["story-1"],
        },
    )
    assert response.status_code == 501
