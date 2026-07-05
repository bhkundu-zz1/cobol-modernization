# Built with repo-root context (see docker-compose.yml).
FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pydantic-settings \
    httpx \
    redis

COPY backend/review_bff/ backend/review_bff/

ENV PYTHONPATH=/app
WORKDIR /app/backend/review_bff
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
