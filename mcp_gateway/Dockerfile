# Built with repo-root context (see docker-compose.yml) since mainframe_tools.py
# imports agents.mainframe_ingestion.adapter — a sibling package.
FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    fastmcp \
    ibmcloudant \
    pydantic \
    pydantic-settings \
    redis \
    httpx \
    pyyaml

COPY mcp_gateway/ mcp_gateway/
COPY agents/ agents/
COPY fixtures/ fixtures/

ENV PYTHONPATH=/app
CMD ["python", "-m", "mcp_gateway.app.main"]
