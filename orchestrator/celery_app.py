"""Celery app configuration — broker/backend/queues from .env (architecture.md section 3.1).

Broker/backend URL is derived from REDIS_HOST/REDIS_PORT/REDIS_DB_CELERY
rather than read as a separate CELERY_BROKER_URL literal — docker-compose
sets REDIS_HOST per-service (e.g. "redis" for the container hostname) but
.env's own CELERY_BROKER_URL default is "localhost", so reading that
directly here would silently ignore docker-compose's override and every
celery worker would try to reach a broker on its own container's
loopback interface instead of the real redis container (confirmed as a
live bug when first bringing up the full stack).
"""

import os

from celery import Celery


def _redis_url(db: int) -> str:
    host = os.environ.get("REDIS_HOST", "localhost")
    port = os.environ.get("REDIS_PORT", "6379")
    password = os.environ.get("REDIS_PASSWORD", "")
    auth = f":{password}@" if password else ""
    return f"redis://{auth}{host}:{port}/{db}"


_REDIS_DB_CELERY = int(os.environ.get("REDIS_DB_CELERY", 0))

app = Celery(
    "harness",
    broker=os.environ.get("CELERY_BROKER_URL") or _redis_url(_REDIS_DB_CELERY),
    backend=os.environ.get("CELERY_RESULT_BACKEND") or _redis_url(_REDIS_DB_CELERY),
    include=[
        "agents.ingestion_chunking.task",
        "agents.cobol_structural.task",
        "agents.jcl_structural.task",
        "agents.recommendation.task",
        "agents.epic_story_writer.task",
        "agents.codegen.task",
    ],
)

app.conf.task_routes = {
    "agents.ingestion_chunking.task.run_ingestion": {"queue": os.environ.get("CELERY_QUEUE_INGESTION", "ingestion")},
    "agents.cobol_structural.task.run_cobol_structural": {"queue": os.environ.get("CELERY_QUEUE_STRUCTURAL", "structural")},
    "agents.jcl_structural.task.run_jcl_structural": {"queue": os.environ.get("CELERY_QUEUE_STRUCTURAL", "structural")},
    "agents.recommendation.task.run_recommendation": {"queue": os.environ.get("CELERY_QUEUE_RECOMMENDATION", "recommendation")},
    "agents.epic_story_writer.task.run_epic_story": {"queue": os.environ.get("CELERY_QUEUE_EPIC_STORY", "epic_story")},
    "agents.codegen.task.run_codegen_task": {"queue": os.environ.get("CELERY_QUEUE_CODEGEN", "codegen")},
}

app.conf.worker_concurrency = int(os.environ.get("CELERY_WORKER_CONCURRENCY", 2))
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]

# Celery's "current app" used by @shared_task-decorated tasks to resolve
# which app they're bound to is normally set per-thread by whichever thread
# imports this module first. FastAPI (via Starlette's run_in_threadpool)
# executes sync route handlers on a worker thread pool, separate from the
# thread that imported this module at process startup — without
# set_default(), a task signature built inside a request handler resolves
# to Celery's own bare, unconfigured default app (broker_url=None) instead
# of this one. Confirmed as a live bug: apply_async() failed with
# "Connection refused" because it was trying to reach the default broker
# (nothing) rather than the real Redis broker configured here.
app.set_default()
