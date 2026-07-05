import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch):
    from agents.tests.conftest import FakeMCPClient

    fake = FakeMCPClient()
    monkeypatch.setattr("app.routes.source_files.get_mcp_client", lambda: fake)
    return TestClient(app), fake


def _seed_source_file(fake, **overrides):
    doc = {
        "_id": "acme-2026:sf-1:source_file",
        "type": "source_file",
        "filename": "PAYROLL01.CBL",
        "language": "cobol",
        "source_text": "IDENTIFICATION DIVISION.",
        "relative_path": "payroll-project/PAYROLL01.CBL",
        **overrides,
    }
    fake.couchdb_write(database="sources", doc=doc, project_id="acme-2026", created_by="test", trace_id="t")


def test_get_source_file_returns_source_text_and_relative_path(client):
    test_client, fake = client
    _seed_source_file(fake)

    response = test_client.get("/source-files/sf-1", params={"project_id": "acme-2026"})
    assert response.status_code == 200
    body = response.json()
    assert body["source_text"] == "IDENTIFICATION DIVISION."
    assert body["relative_path"] == "payroll-project/PAYROLL01.CBL"


def test_get_source_file_returns_null_source_text_for_pre_existing_docs(client):
    test_client, fake = client
    _seed_source_file(fake, source_text=None, relative_path=None)

    response = test_client.get("/source-files/sf-1", params={"project_id": "acme-2026"})
    assert response.status_code == 200
    body = response.json()
    assert body["source_text"] is None
    assert body["relative_path"] is None


def test_get_source_file_not_found_returns_404(client):
    test_client, _ = client
    response = test_client.get("/source-files/nonexistent", params={"project_id": "acme-2026"})
    assert response.status_code == 404
