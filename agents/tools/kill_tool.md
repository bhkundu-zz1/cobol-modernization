# MCP Tool: `kill.check` / `kill.set`

Status: **REAL** — backs `mcp_gateway/app/tools/kill_tools.py` and the
`kill_switch.check()` helper in `agents/common/kill_switch.py`
(architecture.md §7).

## `kill.check`

```
kill_check(
  project_id: str,
  job_run_id: str,
) -> {"killed": bool, "reason": str | None}
```

- Checks, in priority order: `kill:global` → `kill:project:<project_id>` →
  `kill:job:<job_run_id>` in Redis. On a Redis error, falls back to reading
  `job_run.kill_requested` from CouchDB.
- **Fail-safe**: if the check itself can't complete confidently (both Redis
  and CouchDB are unreachable), treat as `killed: true` — never "keep
  running" on uncertainty.
- Every Celery task calls this before each unit of work: at task start,
  before each LLM call, before each MCP tool call, and inside any
  chunk-processing loop for long tasks. On a positive check, the task raises
  a controlled `AgentKilled` exception, marks its `agent_task.status =
  "killed"`, and does not write further recommendation/epic documents.
  Partial output already written stays visible to reviewers.

## `kill.set`

```
kill_set(
  scope: "all" | "project" | "job_run",
  scope_id: str | None,     # required unless scope == "all"
  requested_by: str,
) -> {"ok": bool}
```

- Sets the Redis flag **and** writes the durable CouchDB flag
  (`job_run.kill_requested = true`, or a project-wide marker doc) in the
  same call — Redis alone is not acceptable as the sole record since it's
  not the compliance record of truth and could be flushed.
- Calls `audit.append(event_category="kill_switch")` — every kill request is
  itself an audited action.
- This is the function backing `POST /admin/kill` on the Job/Pipeline
  Control Service (architecture.md §7). A `scope: "all"` request also
  revokes all queued-but-not-yet-started Celery tasks at the API layer
  (`celery.control.revoke(terminate=True)`) — belt-and-suspenders alongside
  the per-task flag check, since revoke alone can race with a task that
  already grabbed work.

## Deferred (see `docs/deferred_scope.md`)

The Guardrails-layer kill check (architecture.md §7's requirement that the
guardrails hop itself honor the kill flag on a long-running generation) is
not implemented this pass, since Guardrails itself is a local stub with no
real container to attach the check to.
