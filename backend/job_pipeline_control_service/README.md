# Job/Pipeline Control Service — internal port 8005

## Status

Marked **[REAL]** in the scaffolding plan. Phase 1 creates folder structure
and a placeholder Dockerfile only. Real FastAPI routes land in **Phase 4**.

## Planned scope (architecture.md sections 3.3, 7)

- `POST /jobs`, `GET /jobs/{id}` — `job_run` lifecycle tracking, mirroring
  Celery task state durably into CouchDB.
- `POST /admin/kill` (`routes/admin.py`) — the real kill-switch endpoint:
  `{scope: "all" | "project:<id>" | "job_run:<id>"}`, restricted to an admin
  role, itself audit-logged (`event_category: kill_switch`). Sets Redis +
  CouchDB flags via the MCP gateway's `kill.set` tool.
- `redis_client.py` — thin wrapper for the kill-flag Redis DB index
  (`REDIS_DB_KILL_FLAGS`, see `.env.example`).

## Planned layout

```
app/
  main.py
  config.py
  redis_client.py
  routes/
    jobs.py
    admin.py
tests/
```
