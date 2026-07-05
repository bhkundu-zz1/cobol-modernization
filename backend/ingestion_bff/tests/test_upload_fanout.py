"""Tests the Ingestion BFF's fan-out to source-mgmt-service and
job-pipeline-control-service using httpx.MockTransport (no live services)."""

import io

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

_RealAsyncClient = httpx.AsyncClient


def _mock_transport(
    *, upload_response=None, mainframe_pull_response=None, mainframe_pull_status=200, job_response=None, job_responses=None
):
    job_responses_iter = iter(job_responses) if job_responses is not None else None

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/uploads":
            return httpx.Response(200, json=upload_response)
        if request.url.path == "/mainframe-pulls":
            return httpx.Response(mainframe_pull_status, json=mainframe_pull_response)
        if request.url.path == "/jobs":
            if job_responses_iter is not None:
                return httpx.Response(202, json=next(job_responses_iter))
            return httpx.Response(202, json=job_response)
        raise AssertionError(f"unexpected request path: {request.url.path}")

    return httpx.MockTransport(handler)


def _patched_async_client(monkeypatch, transport: httpx.MockTransport) -> None:
    def factory(**kwargs):
        kwargs.pop("transport", None)
        return _RealAsyncClient(transport=transport, **kwargs)

    monkeypatch.setattr("app.routes.upload.httpx.AsyncClient", factory)


@pytest.fixture
def client():
    return TestClient(app)


def test_create_upload_fans_out_and_returns_202(client, monkeypatch):
    upload_response = {
        "upload_batch_id": "batch-1",
        "source_upload_id": "su-1",
        "files": [{"source_file_id": "sf-1", "filename": "PAYROLL01.CBL", "sha256": "x", "source_text": "IDENTIFICATION DIVISION."}],
    }
    job_response = {"job_run_id": "jr-1", "status": "running"}

    transport = _mock_transport(upload_response=upload_response, job_response=job_response)
    _patched_async_client(monkeypatch, transport)

    response = client.post(
        "/bff/uploads",
        data={"project_id": "acme-2026"},
        files={"files": ("PAYROLL01.CBL", io.BytesIO(b"IDENTIFICATION DIVISION."), "text/plain")},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["upload_batch_id"] == "batch-1"
    assert body["jobs"] == [{"filename": "PAYROLL01.CBL", "job_run_id": "jr-1"}]


def test_create_upload_triggers_one_job_per_file_in_a_multi_file_batch(client, monkeypatch):
    upload_response = {
        "upload_batch_id": "batch-1",
        "source_upload_id": "su-1",
        "files": [
            {"source_file_id": "sf-1", "filename": "PAYROLL01.CBL", "sha256": "x", "source_text": "A"},
            {"source_file_id": "sf-2", "filename": "TIMESHEET.CBL", "sha256": "y", "source_text": "B"},
        ],
    }
    job_responses = [{"job_run_id": "jr-1", "status": "running"}, {"job_run_id": "jr-2", "status": "running"}]

    transport = _mock_transport(upload_response=upload_response, job_responses=job_responses)
    _patched_async_client(monkeypatch, transport)

    response = client.post(
        "/bff/uploads",
        data={"project_id": "acme-2026"},
        files=[
            ("files", ("PAYROLL01.CBL", io.BytesIO(b"A"), "text/plain")),
            ("files", ("TIMESHEET.CBL", io.BytesIO(b"B"), "text/plain")),
        ],
    )
    assert response.status_code == 202
    body = response.json()
    assert body["jobs"] == [
        {"filename": "PAYROLL01.CBL", "job_run_id": "jr-1"},
        {"filename": "TIMESHEET.CBL", "job_run_id": "jr-2"},
    ]


def test_mainframe_pull_fans_out_and_returns_202(client, monkeypatch):
    pull_response = {
        "upload_batch_id": "batch-2",
        "source_upload_id": "su-2",
        "source_file_id": "sf-2",
        "filename": "PAYROLL01.CBL",
        "source_text": "IDENTIFICATION DIVISION.",
        "scm_element_ref": {"element_id": "PAYROLL01"},
    }
    job_response = {"job_run_id": "jr-2", "status": "running"}

    transport = _mock_transport(mainframe_pull_response=pull_response, job_response=job_response)
    _patched_async_client(monkeypatch, transport)

    response = client.post(
        "/bff/mainframe-pulls",
        json={"project_id": "acme-2026", "tool": "mock", "system": "PAYSYS", "subsystem": "PAYROLL", "element_id": "PAYROLL01"},
    )
    assert response.status_code == 202
    assert response.json()["job_run_id"] == "jr-2"


def test_mainframe_pull_propagates_501_from_source_mgmt(client, monkeypatch):
    transport = _mock_transport(mainframe_pull_response={"detail": "Endevor connector wire protocol not yet implemented"}, mainframe_pull_status=501)
    _patched_async_client(monkeypatch, transport)

    response = client.post(
        "/bff/mainframe-pulls",
        json={"project_id": "acme-2026", "tool": "endevor", "system": "PAYSYS", "subsystem": "PAYROLL", "element_id": "PAYROLL01"},
    )
    assert response.status_code == 501
    assert "not yet implemented" in response.json()["detail"]


def test_create_upload_requires_at_least_one_file(client):
    response = client.post("/bff/uploads", data={"project_id": "acme-2026"}, files=[])
    assert response.status_code in (400, 422)
