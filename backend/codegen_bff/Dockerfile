# Built with repo-root context (see docker-compose.yml).
FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pydantic-settings \
    httpx

COPY backend/codegen_bff/ backend/codegen_bff/

ENV PYTHONPATH=/app
WORKDIR /app/backend/codegen_bff
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8008"]
