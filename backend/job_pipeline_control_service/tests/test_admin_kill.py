import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch):
    from agents.tests.conftest import FakeMCPClient

    fake = FakeMCPClient()
    monkeypatch.setattr("app.routes.admin.get_mcp_client", lambda: fake)
    monkeypatch.setenv("KILL_SWITCH_ADMIN_TOKEN", "test-admin-token")

    class FakeCeleryControl:
        def __init__(self):
            self.purged = False

        def purge(self):
            self.purged = True

    class FakeCeleryApp:
        def __init__(self):
            self.control = FakeCeleryControl()

    fake_celery_app = FakeCeleryApp()
    monkeypatch.setattr("app.routes.admin.celery_app", fake_celery_app)

    return TestClient(app), fake, fake_celery_app


def test_kill_requires_admin_token(client):
    test_client, _, _ = client
    response = test_client.post("/admin/kill", json={"scope": "job_run", "scope_id": "jr-1"})
    assert response.status_code == 403


def test_kill_rejects_wrong_admin_token(client):
    test_client, _, _ = client
    response = test_client.post(
        "/admin/kill", json={"scope": "job_run", "scope_id": "jr-1"}, headers={"x-admin-token": "wrong"}
    )
    assert response.status_code == 403


def test_kill_job_run_scope_succeeds_with_correct_token(client):
    test_client, fake, fake_celery_app = client
    response = test_client.post(
        "/admin/kill",
        json={"scope": "job_run", "scope_id": "jr-1"},
        headers={"x-admin-token": "test-admin-token"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert fake.killed is True
    assert fake_celery_app.control.purged is False, "purge should only happen for scope=all"


def test_kill_all_scope_purges_celery(client):
    test_client, fake, fake_celery_app = client
    response = test_client.post("/admin/kill", json={"scope": "all"}, headers={"x-admin-token": "test-admin-token"})
    assert response.status_code == 200
    assert fake_celery_app.control.purged is True


def test_kill_non_all_scope_requires_scope_id(client):
    test_client, _, _ = client
    response = test_client.post(
        "/admin/kill", json={"scope": "job_run"}, headers={"x-admin-token": "test-admin-token"}
    )
    assert response.status_code == 400
