# Deferred Scope — Vertical Slice Pass

This document tracks what the full architecture (`docs/architecture.md`)
describes that is **not** built in this pass, and why. It exists so a future
engineer picking up any of this work knows exactly what's stubbed, what's
genuinely absent, and what decision produced that gap — not just that a
folder is empty.

The vertical slice this pass builds: **ingest a COBOL source (manual upload
or a mainframe SCM connector pull) → ingestion & chunking agent → COBOL
structural agent → recommendation agent → review queue UI (list, expand for
source/recommendation/backlog detail, approve/reject) → epic/story writer
(manually triggered, project-scoped)**. Everything below is outside that
path.

## Agent logic

- **JCL structural agent** (`agents/jcl_structural/`) — stub task only; it
  marks its `agent_task.status = "skipped"` and does not block the pipeline
  chord. The `jcl-structural-analysis` skill file is written in full so the
  prompt/output contract is settled, but no Celery task actually invokes it
  for real extraction this pass.
- **Epic/Story writer** (`agents/epic_story_writer/`) — real: clusters a
  project's `migration_recommendation`s into epics by shared copybooks/
  call-graph edges (`agents/epic_story_writer/clustering.py`, deterministic,
  not LLM-driven), drafts stories with acceptance criteria citing real
  paragraph names, and propagates confidence scores from the underlying
  structure/recommendation. Unlike stages [1]-[3], it is **not** appended to
  `orchestrator/pipeline.py`'s per-file chain — an epic can span programs
  from separate uploads/job_runs, so it's triggered independently via
  `POST /jobs/generate-epics-stories` (the Review Queue's "Generate Epics &
  Stories" button), consumed by its own `celery-worker-epic-story`
  container/queue. `scripts/seed_epics_stories.py` and its manually-seeded
  fixtures remain useful for testing the Editor MFE/export pipeline in
  isolation, but are no longer the only way epic/story documents get
  created.
- **QA/drilldown** (`agents/qa_drilldown/`) — skill file written in full;
  no FastAPI endpoint or synchronous chat path implemented. See
  `agents/skills/qa-drilldown/SKILL.md` for the intended contract.

## Mainframe connector

- The `mainframe.fetch_source` MCP tool, its adapter registry, and the
  Upload MFE's "connect to mainframe repo" UI **are real** this pass — this
  is not a stub in the usual sense.
- What's actually deferred: the real wire protocols. Only `MockAdapter` is
  runnable (returns fixture content simulating a real pull).
  `EndevorAdapter`, `PanvaletAdapter`, and `ChangemanAdapter` are real
  classes implementing the shared interface (`list_elements`, `get_source`,
  `get_metadata`), but their HTTP calls raise `NotImplementedError` with a
  message naming the protocol still to be built:
  - Endevor → REST API v2 (Endevor Web Services)
  - ChangeMan ZMF → REST API Server (v8.1+)
  - PanValet → no modern REST surface; realistic path is PAM API for
    browsing, or batch-extract via `PAN#1` to a PDS, read via z/OSMF
  - (ISPW and the generic z/OSMF fallback from architecture.md §1a are not
    even stubbed as classes this pass — only the three tools named in the
    plan got adapter stubs.)
- Selecting a real tool in the UI must surface this cleanly as "not yet
  available," never silently fall back to mock data.

## Guardrails and Langfuse

- Both are local, in-process stubs (`agents/common/guardrails_client.py`,
  `agents/common/langfuse_client.py`) — no real NeMo Guardrails container,
  no self-hosted Langfuse stack.
- `guardrails_client.check_output` does perform **real** local
  Pydantic/JSON-schema validation against the expected output shape
  (rejecting/retrying on missing `rationale`/`alternative_considered`/
  `risk_flags`, for example) — this is genuine behavior, just backed by a
  stub instead of the real service.
- The Guardrails-layer kill-switch check (architecture.md §7's requirement
  that the guardrails hop itself honor the kill flag on a long-running
  generation) has nothing real to attach to yet and is deferred alongside
  the real container.

## Issue tracker export (GitHub real, Jira deferred)

- GitHub export **is real** this pass: `agents/issue_tracker_export/adapter.py`'s
  `GitHubAdapter` makes genuine REST calls (`api.github.com`) to create/reuse
  Milestones (Epic) and Issues (Story), the `issue_tracker_export` MCP tool
  writes results back onto the `epic`/`story` documents and audits every
  export, `epic_story_service` + `editor_admin_bff` expose real CRUD/export
  routes, and the Editor MFE's `ExportPanel` drives it end to end. There is
  no separate `export_service` — export logic lives in `epic_story_service`
  plus the MCP gateway, by design (one fewer service to deploy/observe for a
  low-traffic, human-triggered action).
- Jira remains deferred, but as a **real, loudly-failing adapter and UI**,
  not an absent one: `JiraAdapter`'s methods all raise `NotImplementedError`
  naming "Jira Cloud REST API v3" as the missing protocol, the Editor MFE's
  destination picker shows a real Jira connect form, and submitting it
  surfaces the backend's 501 verbatim — the same pattern already proven for
  real (non-mock) mainframe SCM tools.
- `agents/tools/issue_tracker_export_tool.md` documents the unified,
  tool-discriminated MCP tool shape (superseding the old
  `jira_export_tool.md`, which assumed a Jira-only, single-tool design).

## Code generation (GitHub commit real, no filesystem/volume path)

- **Real** this pass: `agents/codegen/task.py` (stage [5], architecture.md
  §3.2/§1c) generates a first-draft microservice for one approved story in
  either Python (`codegen-python` skill) or Java Spring Boot
  (`codegen-java-spring-boot` skill), chosen per generation click, and
  commits the result as one commit to a client-configured GitHub repo via
  the new `codegen.commit_files` MCP tool
  (`mcp_gateway/app/tools/codegen_tools.py`, GitHub Git Data API:
  blob → tree → commit → ref-update, with bounded retry on a concurrent
  ref move). The approval gate is re-verified server-side against every
  source program's `migration_recommendation.human_review_status`, never
  trusting the frontend's eligibility check. `celery-worker-codegen`,
  `codegen_bff` (the approval-gate join + trigger/poll proxy), and the
  Code Generation MFE (port 3005, "approved stories only") are all real
  and wired end to end.
- Nothing is written to a shared filesystem or Docker volume — the
  original COBOL source is never materialized anywhere new; it's read
  from CouchDB (`source_file.source_text`) only to ground the generation
  prompt.
- What's deferred: generation only ever uses the **first** program in a
  multi-program story's `source_program_ids` as its structure/
  understanding/recommendation input (documented as a known limitation in
  `agents/codegen/task.py`'s module docstring) — a story spanning multiple
  COBOL programs does not yet merge their structures into one generation
  prompt. There is also no re-generation diffing (a second "Generate"
  click on an already-generated story simply produces a new commit; it
  does not show the operator a diff against the previous generation
  first).

## Model providers

- `litellm_config.yaml`'s `model_list` still documents `cobol-analysis-oss`
  (vLLM) and `cobol-analysis-dev` (Ollama) entries per architecture.md §4
  for completeness, but no vLLM or Ollama containers are started — only the
  mock/echo model route actually resolves and is reachable this pass.

## Compliance / audit

- Hash-chained `audit_event` documents with real sha256 chaining and
  append-only enforcement (both application-layer and a CouchDB
  `validate_doc_update` design-doc rejection) **are implemented for real**
  this pass — this is explicitly not deferred, since it's the
  compliance-critical piece called out in `CLAUDE.md`.
- What's deferred: the **external audit anchor** (publishing the chain-tip
  hash to an independent, write-once store like S3 Object Lock, so even a
  compromised CouchDB admin can't quietly rewrite history without the
  anchor mismatching). `audit.export_range` exists in basic form
  (chain-walk + a `chain_valid` boolean) but there's no external publish
  job yet. **This is a compliance gap to close before any real
  production/regulatory use** — the hash chain alone proves internal
  consistency, not independence from a compromised database.
- Also deferred: the periodic-beat crash-resume reconciler (architecture.md
  §3.3's 5-minute scan for orphaned `job_run` docs with no live Celery
  heartbeat). Only the per-task checkpoint write is implemented; automatic
  re-enqueue after a worker crash is not.

## Data layer

- **Partitioned CouchDB databases** — all 7 databases are plain
  (non-partitioned) this pass. `project_id` is still present on every
  document and used in every Mango query (architecture.md §2.3's index
  list), so query *correctness* doesn't depend on partitioning; only the
  partition-scoped performance optimization is deferred.
- **`_changes`-feed-driven cache invalidation** — `review_bff`'s cache uses
  a simple Redis TTL (a small number of seconds) instead of subscribing to
  CouchDB's `_changes` feed. This is a genuine tradeoff: a reviewer
  approving an item may see stale review-queue state for up to the TTL
  window on another client. Not silently dropped — flagged here and inline
  in `backend/review_bff/app/cache.py`.

## Frontend

- **Epic/Story Editor MFE** (`frontend/editor-mfe`) is now real: browse
  epics as an expandable accordion, expand a story to view its description,
  acceptance criteria, and traceability back to `source_program_ids`; edit a
  story in place (title/description/acceptance criteria — provenance fields
  like `generated_by_agent` stay read-only); multi-select stories and export
  to GitHub (real) or Jira (real UI, `NotImplementedError` surfaced from the
  backend). It can now browse real agent-generated epics/stories (see
  "Agent logic" above) in addition to manually-seeded fixtures. What's still
  absent: no Jira execution, no bulk edit.
- **Review Queue MFE** (`frontend/review-mfe`) rows are now expandable: each
  row lazily fetches (on first expand, not as part of the list load) and
  shows three panels — real COBOL source text with its captured relative
  path label, the full recommendation reasoning (rationale, alternative
  considered, risk flags, decision factors), and the program's generated
  epic/story with a confidence badge (or a "not yet grouped" message if
  epic/story generation hasn't run for this project yet). A "Generate Epics
  & Stories" button triggers the real epic-story-writer agent for the whole
  project and polls its job status.
- **Admin/Observability MFE** (`frontend/admin-mfe`) still renders a static
  "coming soon" placeholder. Its purpose this pass remains proving Module
  Federation composes all remote slots correctly (including failure
  isolation), not real functionality. No kill-switch button, no Langfuse
  link-out, no audit log viewer UI.
- **Code Generation MFE** (`frontend/codegen-mfe`, port 3005) is real: a
  language picker (Python / Java Spring Boot), a list of stories eligible
  for generation ("approved stories only" — every source program's
  recommendation approved), a per-row Generate button that triggers and
  polls the real codegen agent, and a "view commit" link once generation
  succeeds. See "Code generation" above.

## Deployment

- **Kubernetes manifests** — docker-compose only, per architecture.md's own
  local/dev scoping (§10); Kubernetes is explicitly future work there too,
  not newly deferred by this pass.
