"""Tests the Review BFF's fan-out and Redis-TTL caching, using
httpx.MockTransport (no live services) and an in-memory fake Redis."""

import asyncio
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

_RealAsyncClient = httpx.AsyncClient


class FakeRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value

    def scan_iter(self, match: str):
        prefix = match.rstrip("*")
        return [k for k in list(self._store) if k.startswith(prefix)]

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


RECOMMENDATIONS = {
    "items": [
        {
            "_id": "rec-1",
            "subject_id": "sf-1",
            "subject_filename": "PAYROLL01.CBL",
            "subject_type": "cobol_program",
            "confidence_score": 0.9,
            "human_review_status": "pending",
            "job_run_id": "jr-1",
        },
        {
            "_id": "rec-2",
            "subject_id": "sf-2",
            "subject_filename": "TIMESHEET.CBL",
            "subject_type": "cobol_program",
            "confidence_score": 0.5,
            "human_review_status": "pending",
            "job_run_id": "jr-2",
        },
    ]
}


def _slow_job_status_transport(delay_seconds: float):
    """httpx.MockTransport only supports a sync handler; a blocking
    time.sleep() inside it would stall the whole event loop and defeat the
    point of this test (it would "pass" the concurrency check even for a
    serial implementation, or as seen once during development, fail a
    correct concurrent implementation due to event-loop contention). Using
    an AsyncMockTransport-equivalent handler via httpx's async handler
    support keeps the delay truly async so asyncio.gather's concurrency is
    actually exercised.
    """

    async def async_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/recommendations":
            return httpx.Response(200, json=RECOMMENDATIONS)
        if request.url.path.startswith("/jobs/"):
            await asyncio.sleep(delay_seconds)
            return httpx.Response(200, json={"status": "completed"})
        raise AssertionError(f"unexpected path: {request.url.path}")

    return httpx.MockTransport(async_handler)


@pytest.fixture
def client(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr("app.routes.review_items.get_redis_client", lambda: fake_redis)
    return TestClient(app), fake_redis


def test_list_review_items_fans_out_concurrently(client, monkeypatch):
    test_client, _ = client
    transport = _slow_job_status_transport(delay_seconds=0.2)

    def factory(**kwargs):
        kwargs.pop("transport", None)
        return _RealAsyncClient(transport=transport, **kwargs)

    monkeypatch.setattr("app.routes.review_items.httpx.AsyncClient", factory)

    start = time.monotonic()
    response = test_client.get("/bff/review-items", params={"project_id": "acme-2026"})
    elapsed = time.monotonic() - start

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    # Two job-status lookups at 0.2s each: concurrent => close to 0.2s total,
    # serial would be close to 0.4s. Assert well under the serial time.
    assert elapsed < 0.35, f"expected concurrent fan-out, took {elapsed:.3f}s (serial would be ~0.4s)"


def test_list_review_items_filters_by_min_confidence(client, monkeypatch):
    test_client, _ = client
    transport = _slow_job_status_transport(delay_seconds=0.0)

    def factory(**kwargs):
        kwargs.pop("transport", None)
        return _RealAsyncClient(transport=transport, **kwargs)

    monkeypatch.setattr("app.routes.review_items.httpx.AsyncClient", factory)

    response = test_client.get("/bff/review-items", params={"project_id": "acme-2026", "min_confidence": 0.7})
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["subject_id"] == "sf-1"
    assert body["items"][0]["subject_filename"] == "PAYROLL01.CBL"


def test_list_review_items_uses_cache_on_second_call(client, monkeypatch):
    test_client, fake_redis = client
    call_count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        call_count["n"] += 1
        if request.url.path == "/recommendations":
            return httpx.Response(200, json=RECOMMENDATIONS)
        return httpx.Response(200, json={"status": "completed"})

    transport = httpx.MockTransport(handler)

    def factory(**kwargs):
        kwargs.pop("transport", None)
        return _RealAsyncClient(transport=transport, **kwargs)

    monkeypatch.setattr("app.routes.review_items.httpx.AsyncClient", factory)

    test_client.get("/bff/review-items", params={"project_id": "acme-2026"})
    first_call_count = call_count["n"]
    test_client.get("/bff/review-items", params={"project_id": "acme-2026"})

    assert call_count["n"] == first_call_count, "second call should be served from cache, no new HTTP calls"


def test_decision_invalidates_cache(client, monkeypatch):
    test_client, fake_redis = client
    fake_redis.set("review-items:acme-2026:all", '{"items": [], "bookmark": null}')

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"recommendation_id": "rec-1", "human_review_status": "approved"})

    transport = httpx.MockTransport(handler)

    def factory(**kwargs):
        kwargs.pop("transport", None)
        return _RealAsyncClient(transport=transport, **kwargs)

    monkeypatch.setattr("app.routes.review_items.httpx.AsyncClient", factory)

    response = test_client.post(
        "/bff/review-items/rec-1/decision",
        params={"project_id": "acme-2026"},
        json={"decision": "approved", "reviewed_by": "bhakti.kundu@gmail.com"},
    )
    assert response.status_code == 200
    assert fake_redis.get("review-items:acme-2026:all") is None
