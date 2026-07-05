# Epic/Story-Writer Agent — [STUB]

## What will eventually live here

Per architecture.md section 3.2 stage [4]: groups recommendations into
epics (by subsystem/copybook-sharing cluster, detected via call-graph
connected-components, not per-file 1:1); drafts stories with acceptance
criteria referencing specific COBOL paragraphs/JCL steps for traceability;
writes `epic`/`story` docs (`human_review` pending) via MCP.

## Why this is a stub this pass

`docs/deferred_scope.md` lists epic/story real logic as explicitly
deferred. Per the plan's "Key interfaces" section: "Epic/story stage is not
appended this pass — `job_run` completes once recommendations are written."
The vertical slice ends at the review queue (recommendations), not epics/
stories, so this agent's `task.py` (added in Phase 3) is not wired into the
Celery chain at all — it exists as a folder/placeholder for the pipeline
stage architecture.md describes, but nothing invokes it yet.

See `docs/deferred_scope.md` for the full reasoning.
