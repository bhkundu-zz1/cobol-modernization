import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch):
    from agents.tests.conftest import FakeMCPClient

    fake = FakeMCPClient()
    monkeypatch.setattr("app.routes.recommendations.get_mcp_client", lambda: fake)
    return TestClient(app), fake


def _seed_recommendation(fake, **overrides):
    doc = {
        "type": "migration_recommendation",
        "subject_type": "cobol_program",
        "subject_id": "sf-1",
        "recommended_target": "python_microservice",
        "rationale": "low complexity",
        "confidence_score": 0.9,
        "decision_factors": {},
        "alternative_considered": {"target": "java_spring_boot", "why_rejected": "n/a"},
        "risk_flags": [],
        "produced_by_agent": "recommendation@v1",
        "produced_by_model": "cobol-analysis-dev",
        "human_review_status": "pending",
        **overrides,
    }
    result = fake.couchdb_write(database="recommendations", doc=doc, project_id="acme-2026", created_by="agent:test", trace_id="t")
    return result["id"]


def test_list_recommendations_filters_by_project(client):
    test_client, fake = client
    _seed_recommendation(fake)
    response = test_client.get("/recommendations", params={"project_id": "acme-2026"})
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_list_recommendations_filters_by_human_review_status(client):
    test_client, fake = client
    _seed_recommendation(fake, human_review_status="pending")
    _seed_recommendation(fake, human_review_status="approved")
    response = test_client.get("/recommendations", params={"project_id": "acme-2026", "human_review_status": "approved"})
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["human_review_status"] == "approved"


def test_get_recommendation_not_found(client):
    test_client, _ = client
    response = test_client.get("/recommendations/nonexistent")
    assert response.status_code == 404


def test_record_decision_updates_status_and_audits(client):
    test_client, fake = client
    rec_id = _seed_recommendation(fake)

    response = test_client.post(
        f"/recommendations/{rec_id}/decision",
        json={"decision": "approved", "reviewed_by": "bhakti.kundu@gmail.com"},
    )
    assert response.status_code == 200
    assert response.json()["human_review_status"] == "approved"

    doc = fake.databases["recommendations"][rec_id]
    assert doc["human_review_status"] == "approved"
    assert doc["reviewed_by"] == "bhakti.kundu@gmail.com"
    assert doc["reviewed_at"]

    assert len(fake.audit_events) == 1
    assert fake.audit_events[0]["event_category"] == "human_review_decision"
