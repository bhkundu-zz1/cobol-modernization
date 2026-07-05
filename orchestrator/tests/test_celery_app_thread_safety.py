"""Regression test: building a pipeline signature from a worker thread other
than the one that first imported orchestrator.celery_app must still resolve
to the properly-configured `harness` Celery app, not celery's own bare
default app (broker_url=None). This broke once under FastAPI's
run_in_threadpool, which runs sync route handlers on a thread distinct from
the one that imported celery_app at process startup — celery's "current
app" resolution is thread-sensitive without app.set_default()."""

import threading

import orchestrator.celery_app  # noqa: F401 - import triggers app.set_default()


def test_pipeline_built_from_a_different_thread_uses_the_configured_broker():
    results: dict[str, str | None] = {}

    def worker() -> None:
        from orchestrator.pipeline import build_pipeline

        pipeline = build_pipeline(
            project_id="acme-2026",
            job_run_id="jr-thread-test",
            upload_batch_id="batch-1",
            source_file_id="sf-1",
            filename="X.CBL",
            source_text="X",
            source_origin="manual_upload",
        )
        results["broker_url"] = pipeline.app.conf.broker_url

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert results["broker_url"] is not None
    assert results["broker_url"] == orchestrator.celery_app.app.conf.broker_url
