# Redis — usage notes

## Status

**[STUB]** — this is a documentation-only folder; there is no dedicated
Redis application code to scaffold beyond what already lives in
`agents/common/kill_switch.py`, `orchestrator/celery_app.py`, and the BFF
cache modules (all Phase 2/3/4 work).

## DB-index convention (single Redis instance, logically partitioned)

Per `.env.example` and architecture.md sections 3.1, 7, 9.1, this project
runs one Redis instance locally and splits it by logical DB index rather
than running three separate Redis containers:

| DB index | Purpose | Owning components |
|---|---|---|
| 0 | Celery broker + result backend | `orchestrator/celery_app.py` |
| 1 | General-purpose cache (BFF fan-out responses, skill-file content with TTL + git-commit-hash cache-busting key, `model_policy` lookups) | `backend/review_bff`, `backend/ingestion_bff`, `agents/common/skill_loader.py` |
| 2 | Kill-switch flags (`kill:global`, `kill:project:<id>`, `kill:job:<id>`) | `agents/common/kill_switch.py`, `mcp_gateway/app/tools/kill_tools.py`, `backend/job_pipeline_control_service` |

Environment variables: `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`,
`REDIS_DB_CELERY`, `REDIS_DB_CACHE`, `REDIS_DB_KILL_FLAGS` (see
`.env.example`).

## Why DB-index separation, not three containers

Simpler local dev topology (one container to run/monitor) while keeping the
three concerns logically isolated enough that a `FLUSHDB` against the cache
index, for example, can never accidentally wipe kill-switch flags or Celery
queue state. Production HA (Sentinel/Cluster) is a documented upgrade path
per architecture.md section 10, not a Phase 1 concern.

## Deferred

The `_changes`-feed-driven cache invalidation subscriber described in
architecture.md section 9.1 is deferred in favor of a simple TTL
(`CACHE_TTL_SECONDS` in `.env.example`) — a real staleness tradeoff, called
out in `docs/deferred_scope.md`, not silently dropped.
