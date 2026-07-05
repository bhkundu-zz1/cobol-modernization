FROM python:3.11-slim
WORKDIR /app
COPY infra/mock_llm/pyproject.toml ./
RUN pip install --no-cache-dir fastapi "uvicorn[standard]"
COPY infra/mock_llm/server.py ./
CMD ["python", "server.py"]
