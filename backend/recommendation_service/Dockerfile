# Built with repo-root context (see docker-compose.yml).
FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pydantic-settings \
    httpx \
    fastmcp

COPY agents/common/ agents/common/
COPY agents/__init__.py agents/__init__.py
COPY backend/shared/ backend/shared/
COPY backend/recommendation_service/ backend/recommendation_service/

ENV PYTHONPATH=/app
WORKDIR /app/backend/recommendation_service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006"]
