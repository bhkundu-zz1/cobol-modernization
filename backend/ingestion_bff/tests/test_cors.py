"""Regression test: the browser (shell + upload-mfe) calls this BFF directly
via fetch(). Without CORS headers the request is blocked client-side with
no server-visible error at all — confirmed as a live bug the first time
this ran through an actual browser rather than curl/TestClient."""

from fastapi.testclient import TestClient

from app.main import app


def test_preflight_allows_the_shell_origin():
    client = TestClient(app)
    response = client.options(
        "/bff/uploads",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_preflight_allows_the_upload_mfe_origin():
    client = TestClient(app)
    response = client.options(
        "/bff/uploads",
        headers={"Origin": "http://localhost:3001", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3001"
