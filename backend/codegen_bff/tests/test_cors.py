"""Regression test: the browser (shell + codegen-mfe, served on their own
ports) calls this BFF directly via fetch(). Without CORS headers the
request is blocked client-side with no server-visible error at all."""

from fastapi.testclient import TestClient

from app.main import app


def test_preflight_allows_the_shell_origin():
    client = TestClient(app)
    response = client.options(
        "/bff/codegen/eligible-stories",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_preflight_allows_the_codegen_mfe_origin():
    client = TestClient(app)
    response = client.options(
        "/bff/codegen/eligible-stories",
        headers={"Origin": "http://localhost:3005", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3005"
