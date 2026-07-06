import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch):
    from agents.tests.conftest import FakeMCPClient

    fake = FakeMCPClient()
    monkeypatch.setattr("app.routes.jobs.get_mcp_client", lambda: fake)

    class ImmediateResult:
        def apply_async(self_inner):
            return None

    monkeypatch.setattr("app.routes.jobs.build_pipeline", lambda **kwargs: ImmediateResult())

    epic_story_calls = []
    monkeypatch.setattr(
        "app.routes.jobs.run_epic_story.delay",
        lambda project_id, job_run_id, agent_task_id: epic_story_calls.append((project_id, job_run_id, agent_task_id)),
    )

    codegen_calls = []
    monkeypatch.setattr(
        "app.routes.jobs.run_codegen_task.delay",
        lambda project_id, job_run_id, agent_task_id, story_id, target_language: codegen_calls.append(
            (project_id, job_run_id, agent_task_id, story_id, target_language)
        ),
    )

    return TestClient(app), fake, epic_story_calls, codegen_calls


def test_trigger_job_returns_202_with_job_run_id(client):
    test_client, _, _, _ = client
    response = test_client.post(
        "/jobs",
        json={
            "project_id": "acme-2026",
            "upload_batch_id": "batch-1",
            "source_file_id": "sf-1",
            "filename": "PAYROLL01.CBL",
            "source_text": "IDENTIFICATION DIVISION.",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["job_run_id"]
    assert body["status"] == "running"


def test_get_job_not_found_returns_404(client):
    test_client, _, _, _ = client
    response = test_client.get("/jobs/nonexistent-job", params={"project_id": "acme-2026"})
    assert response.status_code == 404


def test_get_job_returns_job_run_doc(client):
    test_client, fake, _, _ = client
    fake.couchdb_write(
        database="agent_runs",
        doc={"_id": "acme-2026:jr-1:job_run", "type": "job_run", "job_run_id": "jr-1", "status": "completed"},
        project_id="acme-2026",
        created_by="system:test",
        trace_id="jr-1",
    )
    response = test_client.get("/jobs/jr-1", params={"project_id": "acme-2026"})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_generate_epics_stories_returns_202_and_triggers_task(client):
    test_client, _, epic_story_calls, _ = client
    response = test_client.post("/jobs/generate-epics-stories", json={"project_id": "acme-2026"})
    assert response.status_code == 202
    body = response.json()
    assert body["job_run_id"]
    assert body["status"] == "running"
    assert len(epic_story_calls) == 1
    assert epic_story_calls[0][0] == "acme-2026"


def test_generate_code_returns_202_and_triggers_task_with_story_id_and_language(client):
    test_client, _, _, codegen_calls = client
    response = test_client.post(
        "/jobs/generate-code",
        json={"project_id": "acme-2026", "story_id": "story-a", "target_language": "python"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["job_run_id"]
    assert body["status"] == "running"
    assert len(codegen_calls) == 1
    project_id, job_run_id, agent_task_id, story_id, target_language = codegen_calls[0]
    assert project_id == "acme-2026"
    assert story_id == "story-a"
    assert target_language == "python"
