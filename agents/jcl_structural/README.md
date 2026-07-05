# JCL Structural Agent — [STUB]

## What will eventually live here

Per architecture.md section 3.2 stage [2b]: extract JCL steps, DD
statements, COND/RC logic, PROC expansion; build a step dependency graph;
infer schedule cadence from naming/comments (heuristic, flagged as inferred
not fact); compute a `confidence_score`; write `jcl_job_structure` via MCP.

## Why this is a stub this pass

`docs/deferred_scope.md` lists "JCL ... real logic" as explicitly deferred.
The vertical slice this repo scaffolds around is COBOL-only (ingest ->
COBOL structural -> recommendation -> review queue); JCL structural analysis
is architecturally identical in shape (same pipeline stage, same
`agent_task`/`job_run` mechanics) but real extraction logic is follow-on
work once the COBOL path is proven.

`task.py` (added in Phase 3) will mark its `agent_task.status = "skipped"`
immediately rather than doing no-op fake analysis, so the Celery chord for a
batch containing JCL files still completes correctly and the review queue
never shows fabricated JCL structure.

See `docs/deferred_scope.md` for the full reasoning.
