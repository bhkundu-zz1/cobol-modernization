# Built with repo-root context (see docker-compose.yml). WORKDIR is this
# service's own directory (matching how its tests run: `app.main:app`
# resolves relative imports the same way `pytest` does locally), but
# PYTHONPATH also includes the repo root so `agents.common.mcp_client`
# resolves.
FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pydantic-settings \
    httpx \
    python-multipart \
    fastmcp

COPY agents/ agents/
COPY backend/shared/ backend/shared/
COPY backend/source_mgmt_service/ backend/source_mgmt_service/
COPY fixtures/ fixtures/

ENV PYTHONPATH=/app
WORKDIR /app/backend/source_mgmt_service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
