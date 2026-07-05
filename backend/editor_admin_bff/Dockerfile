# Built with repo-root context (see docker-compose.yml).
FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pydantic-settings \
    httpx

COPY backend/editor_admin_bff/ backend/editor_admin_bff/

ENV PYTHONPATH=/app
WORKDIR /app/backend/editor_admin_bff
ENV EDITOR_ADMIN_BFF_PORT=8003
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${EDITOR_ADMIN_BFF_PORT}"]
