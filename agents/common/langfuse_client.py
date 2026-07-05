"""Local Langfuse stub (architecture.md section 6.1).

No self-hosted Langfuse stack is called this pass — see
docs/deferred_scope.md. trace() logs span start/end locally as a
context manager with the same signature a real Langfuse-backed
implementation would have, so it can be swapped in later via .env
(LANGFUSE_ENABLED=true, LANGFUSE_HOST/keys) without touching call sites.
"""

import logging
import time
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger("langfuse_client")


@contextmanager
def trace(job_run_id: str, agent_task_id: str, name: str) -> Iterator[None]:
    """Every agent task opens one trace (trace_id = job_run_id:agent_task_id
    per architecture.md section 4); every LLM call/guardrail check/MCP tool
    call would nest under it in a real Langfuse-backed implementation."""
    trace_id = f"{job_run_id}:{agent_task_id}"
    start = time.monotonic()
    # `name` (and several other keys) are reserved LogRecord attributes —
    # passing them via `extra` raises KeyError("Attempt to overwrite ...")
    # at log-call time, confirmed as a live bug the first time this ran
    # inside a Celery worker. Prefixed as span_name/span_* to avoid any
    # stdlib LogRecord attribute collision.
    logger.info(
        "langfuse.trace start (stub, local log only)", extra={"trace_id": trace_id, "span_name": name}
    )
    try:
        yield
    finally:
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "langfuse.trace end (stub, local log only)",
            extra={"trace_id": trace_id, "span_name": name, "span_duration_ms": duration_ms},
        )
