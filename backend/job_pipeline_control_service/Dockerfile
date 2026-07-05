# Built with repo-root context (see docker-compose.yml). Needs orchestrator/
# (build_pipeline, celery_app for triggering jobs / purging queues) and the
# full agents/ tree (the 3 real Celery task modules orchestrator imports).
FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pydantic-settings \
    httpx \
    redis \
    "celery[redis]" \
    pyyaml \
    fastmcp

COPY agents/ agents/
COPY orchestrator/ orchestrator/
COPY backend/shared/ backend/shared/
COPY backend/job_pipeline_control_service/ backend/job_pipeline_control_service/
COPY fixtures/ fixtures/

ENV PYTHONPATH=/app
WORKDIR /app/backend/job_pipeline_control_service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
