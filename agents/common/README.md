# Agents Common — shared libraries every agent task uses

## Status

Marked **[REAL]** in the scaffolding plan. Phase 1 creates folder structure
only. Real content lands in **Phase 3**.

## Planned modules (architecture.md sections 3, 4, 5, 6, 7; plan's ground rules)

- `mcp_client.py` — HTTP wrapper; the *only* way agent code reaches the MCP
  gateway (agents never talk to CouchDB or any external system directly).
- `guardrails_client.py` — `check_input()` / `check_output()`. Real local
  Pydantic schema validation this pass; the actual NeMo Guardrails HTTP hop
  is stubbed (see `docs/deferred_scope.md`) but the call sites exist in the
  correct order: agent -> guardrails_client.check_input -> LiteLLM ->
  provider -> guardrails_client.check_output -> agent.
- `langfuse_client.py` — `trace(job_run_id, agent_task_id)` context manager;
  stub that logs locally instead of calling a real Langfuse instance.
- `kill_switch.py` — `kill_switch.check()`; real Redis-first,
  CouchDB-fallback logic, fail-safe to `killed=True` if uncertain
  (architecture.md section 7).
- `llm_client.py` — calls the LiteLLM proxy by logical model name; wraps
  guardrails calls per the call order above.
- `skill_loader.py` — loads a `SKILL.md`, computes its `skill_version_hash`
  (sha256 of file content) at task start.
- `confidence.py` — shared confidence-score computation (architecture.md
  section 3.4): chunk count, self-check discrepancy count, unresolved
  external calls/copybooks.

## Planned layout

```
mcp_client.py
guardrails_client.py
langfuse_client.py
kill_switch.py
llm_client.py
skill_loader.py
confidence.py
```

Note: per the plan, the *canonical* `mcp_client` implementation actually
lives at `backend/shared/mcp_client.py` and is imported here as a local path
dependency — see `backend/shared/README.md`.
