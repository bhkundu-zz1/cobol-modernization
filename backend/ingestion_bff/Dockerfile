# Built with repo-root context (see docker-compose.yml).
FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pydantic-settings \
    httpx \
    python-multipart

COPY backend/ingestion_bff/ backend/ingestion_bff/

ENV PYTHONPATH=/app
WORKDIR /app/backend/ingestion_bff
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
