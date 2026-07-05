# Built with repo-root context (see docker-compose.yml): the Celery worker
# needs agents/ (task implementations) and backend/shared/ (mcp_client,
# document models). The actual worker command (which queue to serve) is
# supplied per-service in docker-compose.yml's `command:` override.
FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    "celery[redis]" \
    redis \
    httpx \
    pydantic \
    pyyaml \
    fastmcp

COPY agents/ agents/
COPY orchestrator/ orchestrator/
COPY backend/shared/ backend/shared/
COPY fixtures/ fixtures/

ENV PYTHONPATH=/app
CMD ["celery", "-A", "orchestrator.celery_app", "worker", "--loglevel=INFO"]
