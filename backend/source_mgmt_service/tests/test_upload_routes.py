import io

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch):
    from agents.tests.conftest import FakeMCPClient

    fake = FakeMCPClient()
    monkeypatch.setattr("app.routes.uploads.get_mcp_client", lambda: fake)
    monkeypatch.setattr("app.routes.mainframe_pulls.get_mcp_client", lambda: fake)
    return TestClient(app), fake


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_upload_writes_source_upload_doc(client):
    test_client, fake = client
    response = test_client.post(
        "/uploads",
        data={"project_id": "acme-2026"},
        files={"files": ("PAYROLL01.CBL", io.BytesIO(b"IDENTIFICATION DIVISION."), "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["upload_batch_id"]
    assert len(body["files"]) == 1

    doc = fake.databases["sources"][body["source_upload_id"]]
    assert doc["type"] == "source_upload"
    assert doc["source_origin"] == "manual_upload"


def test_create_upload_captures_relative_path_when_provided(client):
    test_client, _ = client
    response = test_client.post(
        "/uploads",
        data={"project_id": "acme-2026", "relative_paths": "payroll-project/PAYROLL01.CBL"},
        files={"files": ("PAYROLL01.CBL", io.BytesIO(b"IDENTIFICATION DIVISION."), "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["files"][0]["relative_path"] == "payroll-project/PAYROLL01.CBL"


def test_create_upload_relative_path_is_none_when_not_provided(client):
    test_client, _ = client
    response = test_client.post(
        "/uploads",
        data={"project_id": "acme-2026"},
        files={"files": ("PAYROLL01.CBL", io.BytesIO(b"IDENTIFICATION DIVISION."), "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["files"][0]["relative_path"] is None


def test_create_upload_requires_at_least_one_file(client):
    test_client, _ = client
    response = test_client.post("/uploads", data={"project_id": "acme-2026"}, files=[])
    assert response.status_code in (400, 422)


def test_mainframe_pull_mock_tool_succeeds(client):
    test_client, fake = client
    response = test_client.post(
        "/mainframe-pulls",
        json={"project_id": "acme-2026", "tool": "mock", "system": "PAYSYS", "subsystem": "PAYROLL", "element_id": "PAYROLL01"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "PROGRAM-ID. PAYROLL01" in body["source_text"]
    assert body["scm_element_ref"]["element_id"] == "PAYROLL01"

    doc = fake.databases["sources"][body["source_upload_id"]]
    assert doc["source_origin"] == "mainframe_scm"


def test_mainframe_pull_real_tool_returns_501(client):
    test_client, _ = client
    response = test_client.post(
        "/mainframe-pulls",
        json={"project_id": "acme-2026", "tool": "endevor", "system": "PAYSYS", "subsystem": "PAYROLL", "element_id": "PAYROLL01"},
    )
    assert response.status_code == 501
    assert "not yet implemented" in response.json()["detail"]
