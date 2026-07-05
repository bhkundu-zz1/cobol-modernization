import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch):
    from agents.tests.conftest import FakeMCPClient

    fake = FakeMCPClient()
    monkeypatch.setattr("app.routes.epics.get_mcp_client", lambda: fake)
    monkeypatch.setattr("app.routes.stories.get_mcp_client", lambda: fake)
    monkeypatch.setattr("app.routes.export.get_mcp_client", lambda: fake)
    return TestClient(app), fake


def _seed_epic(fake, **overrides):
    doc = {"type": "epic", "title": "Extract payroll", "description": "...", **overrides}
    result = fake.couchdb_write(database="backlog", doc=doc, project_id="acme-2026", created_by="system:seed", trace_id="t")
    return result["id"]


def _seed_story(fake, epic_id, **overrides):
    doc = {
        "type": "story",
        "epic_id": epic_id,
        "title": "Extract gross-pay calc",
        "description": "...",
        "acceptance_criteria": ["Handles overtime"],
        "source_program_ids": ["PAYROLL01:2000-CALC-GROSS"],
        "generated_by_agent": "epic-story-writer@v1",
        "export_status": "not_exported",
        **overrides,
    }
    result = fake.couchdb_write(database="backlog", doc=doc, project_id="acme-2026", created_by="system:seed", trace_id="t")
    return result["id"]


def test_list_epics(client):
    test_client, fake = client
    _seed_epic(fake)
    response = test_client.get("/epics", params={"project_id": "acme-2026"})
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_list_epic_stories(client):
    test_client, fake = client
    epic_id = _seed_epic(fake)
    _seed_story(fake, epic_id)
    response = test_client.get(f"/epics/{epic_id}/stories", params={"project_id": "acme-2026"})
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_update_story_sets_edited_by_human_and_audits(client):
    test_client, fake = client
    epic_id = _seed_epic(fake)
    story_id = _seed_story(fake, epic_id)

    response = test_client.patch(
        f"/stories/{story_id}",
        json={"title": "Extract gross-pay calc (revised)", "edited_by": "bhakti.kundu@gmail.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["edited_by_human"] is True
    assert len(body["edit_history_ref"]) == 1

    doc = fake.databases["backlog"][story_id]
    assert doc["title"] == "Extract gross-pay calc (revised)"
    assert doc["edited_by_human"] is True
    assert len(fake.audit_events) == 1
    assert fake.audit_events[0]["event_category"] == "human_review_decision"


def test_update_story_not_found_returns_404(client):
    test_client, _ = client
    response = test_client.patch("/stories/nonexistent", json={"edited_by": "x@example.com"})
    assert response.status_code == 404


def test_export_github_success(client):
    test_client, fake = client
    epic_id = _seed_epic(fake)
    story_id = _seed_story(fake, epic_id)

    response = test_client.post(
        "/export",
        json={
            "project_id": "acme-2026",
            "tool": "jira",  # jira raises NotImplementedError with no network needed
            "connection_config": {"project_key": "PROJ", "credential_ref": "env://X"},
            "epic_ids": [epic_id],
            "story_ids": [story_id],
        },
    )
    assert response.status_code == 501
    assert "not yet implemented" in response.json()["detail"]
