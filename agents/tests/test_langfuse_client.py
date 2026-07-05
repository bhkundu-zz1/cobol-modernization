"""Regression test: trace() must not pass reserved LogRecord attribute names
(e.g. "name") via `extra=`, which raises KeyError("Attempt to overwrite
'name' in LogRecord") at log-call time — a live bug the first time this ran
inside an actual Celery worker process (this doesn't reproduce under
pytest's default logging capture, which is why it wasn't caught until then).
"""

import logging

from agents.common.langfuse_client import trace


def test_trace_does_not_raise_when_a_real_handler_is_attached(caplog):
    """caplog attaches a real logging.Handler + calls makeRecord, exercising
    the same code path that raised KeyError in production."""
    with caplog.at_level(logging.INFO, logger="langfuse_client"):
        with trace(job_run_id="jr-1", agent_task_id="task-1", name="ingestion_chunking"):
            pass

    messages = [r.message for r in caplog.records]
    assert any("trace start" in m for m in messages)
    assert any("trace end" in m for m in messages)


def test_trace_reraises_exceptions_from_the_wrapped_block():
    try:
        with trace(job_run_id="jr-1", agent_task_id="task-1", name="cobol_structural"):
            raise ValueError("boom")
        assert False, "expected ValueError to propagate"
    except ValueError:
        pass
