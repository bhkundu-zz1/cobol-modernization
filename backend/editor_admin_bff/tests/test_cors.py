"""Regression test: the browser (shell + editor-mfe, served on their own
ports) calls this BFF directly via fetch(). Without CORS headers the
request is blocked client-side with no server-visible error at all —
mirrors review_bff's test_cors.py, which caught this as a live bug."""

from fastapi.testclient import TestClient

from app.main import app


def test_preflight_allows_the_shell_origin():
    client = TestClient(app)
    response = client.options(
        "/bff/epics",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_preflight_allows_the_editor_mfe_origin():
    client = TestClient(app)
    response = client.options(
        "/bff/epics",
        headers={"Origin": "http://localhost:3003", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3003"
