# Orchestrator — Celery pipeline wiring

## Status

Marked **[REAL]** in the scaffolding plan. Phase 1 creates folder structure
and a placeholder Dockerfile only. Real content lands in **Phase 3**.
`orchestrator/pipeline.py` is one of the plan's "critical files."

## Planned scope (architecture.md section 3, plan's "Key interfaces")

- `celery_app.py` — Celery app config, broker/backend from `.env`
  (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`), one queue per stage
  (`CELERY_QUEUE_INGESTION`, `_STRUCTURAL`, `_RECOMMENDATION`,
  `_EPIC_STORY`).
- `pipeline.py` — `chain(run_ingestion.s(...), chord(group(run_cobol_structural.s(...)
  for cobol/copybook files) | group(run_jcl_structural.s(...) for jcl files),
  run_recommendation_batch.s(...)))`. Epic/story stage is not appended this
  pass.
- `checkpoint.py` — writes `job_run.tasks[i]` via MCP after every task
  (crash-resume compensating control, architecture.md section 3.3).

## Planned layout

```
celery_app.py
pipeline.py
checkpoint.py
tests/
  test_pipeline_wiring.py
```
