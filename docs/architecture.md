# COBOL/JCL Migration Harness — Architecture

This document describes the architecture for the COBOL/JCL migration harness: an application that uses LLM agents to read COBOL and JCL source, reason about it, and produce research, recommendations, epics, and stories to guide clients' migration efforts. It is the authoritative design reference required by this repo's `CLAUDE.md` and must be kept current before any GitHub publish.

Status: architecture-only. No application source exists yet in this repository.

## 0. Key decisions and open risks

### Decisive technology choices

- **CouchDB client**: `ibmcloudant` (the actively maintained Cloudant Python SDK, CouchDB-3.x compatible). `couchdb-python` is unmaintained; `python-cloudant` is deprecated in favor of this.
- **LLM gateway**: LiteLLM Proxy, self-hosted, its own container, pinned to a specific version tag — never `main`/`latest`.
- **Guardrails**: NeMo Guardrails run as its own FastAPI microservice, called as an HTTP hop before/after every LLM call — not embedded as a library inside each agent process, so guardrail policy can change without redeploying agents.
- **Agent orchestration**: Celery + Redis (broker + result backend) for the pipeline DAG, not Temporal or Airflow. See §3.1 for rationale.
- **Async job tracking**: Celery task state is mirrored into CouchDB `job_run` documents. Celery's own backend is ephemeral/opaque; compliance needs a durable, queryable record.
- **MCP gateway**: a single FastMCP-based service exposing tools (`couchdb.read`, `couchdb.write`, `issue_tracker_export`, `file.fetch_source`, `mainframe.fetch_source`, `audit.append`, `kill.check`, etc.) — the only path from agent code to any data store or external API.
- **Mainframe SCM connector**: source ingestion also supports pulling directly from a client's mainframe source/change-management tool (Endevor, ChangeMan ZMF, ISPW, or PanValet-via-z/OSMF), not just manual file upload — see §1a.
- **Issue tracker export surface**: GitHub Issues REST API (Milestones + Issues), not Projects v2 GraphQL — see §1b. Jira export is designed (a real, loudly-failing adapter and UI) but not implemented this pass.
- **Micro frontend composition**: Module Federation 2.0 (via `@module-federation/vite` or the rspack MF plugin), runtime-composed by a lightweight React shell. Not single-spa (an unneeded second orchestration layer here) and not iframes (breaks shared auth/session and cross-MFE navigation).
- **Compliance strategy**: the SEC's 2023 Rule 17a-4 "audit-trail alternative" (not literal WORM hardware) — an append-only, timestamped, tamper-evident audit trail with cryptographic hash chaining, backed by CouchDB plus an externally anchored ledger. Detailed in §6.

### Open risks to confirm before implementation

1. **Regulatory scope ambiguity.** SEC Rule 17a-4 applies to broker-dealers; US Treasury/OCC/FDIC rules apply to banks. This harness is a vendor tool *used by* such regulated entities, not itself regulated — its real obligation is likely "produce audit records our bank/broker-dealer clients can rely on for their own exams," which may be stricter in some ways since the client's specific regulator is unknown up front. Confirm with legal which framework(s) apply (17a-4, SOX, OCC 2011-12/SR 11-7 model risk management, GLBA safeguards, or several) — this affects retention length. A 7-year retention default is assumed below pending that confirmation.
2. **Is an LLM output a "record"?** It's legally unsettled whether an LLM-generated recommendation is a "communication"/"record" under 17a-4 the way a trade blotter is. This design treats it conservatively (log everything, immutable) but the legal question needs client counsel sign-off.
3. **Source code confidentiality vs. commercial LLM APIs.** Client COBOL/JCL may contain embedded secrets (hardcoded credentials, account numbers in copybooks/test data). Sending this to commercial LLM APIs is a data-residency/confidentiality concern distinct from financial audit compliance. Mitigated by a redaction/secret-scanning pre-pass (§3.2) and a per-client policy on which programs are OSS-model-only vs. commercial-API-eligible — needs explicit sign-off on the default policy.
4. **LLM-native parsing context-window limits** (accepted tradeoff). Chunking, self-check passes, and confidence scoring mitigate this (§3.4), but very large COBOL programs (20,000+ lines) or deeply nested JCL PROCs may still produce lower-confidence extraction. Confidence scores are surfaced to human reviewers rather than silently trusted.
5. **Module Federation shared-dependency drift.** Independently deployed MFEs upgrading shared libraries (React, design system) out of sync is MF's classic failure mode. Needs a shared-dependency governance policy, not just a technical guard (§8).
6. **Mainframe connectivity is client-specific and not yet confirmed.** Which SCM tool a given client runs (Endevor, ChangeMan ZMF, ISPW, or PanValet), which auth mechanism their z/OS security team supports (Zowe token, mTLS cert, basic auth over TLS), and whether a DMZ/API gateway already exists in front of the mainframe are all open per-engagement questions (§1a). Endevor is assumed as the default best-supported case; the connector design must not hard-code that assumption.

## 1. System component diagram

```
                                   +-----------------------------------------------------------+
                                   |                    Browser (per user)                      |
                                   |                                                             |
                                   |   +--------------+    loads via runtime import              |
                                   |   |  Shell App   |<--------------------------+              |
                                   |   | (host, :3000)|                           |              |
                                   |   +------+-------+                           |              |
                                   |          | Module Federation remoteEntry.js  |              |
                                   |  +-------+----------+-----------+-----------+              |
                                   |  v       v          v           v                           |
                                   | +------++----------++----------++--------------+            |
                                   | |Upload||  Review   ||  Epic/    ||  Admin/     |            |
                                   | |/Ingest||  Queue    ||  Story    ||  Observ.    |            |
                                   | | MFE   ||  Dashboard||  Editor   ||  MFE        |            |
                                   | | :3001 ||  MFE:3002 ||  MFE:3003 ||  :3004      |            |
                                   | +---+---++-----+-----++-----+-----++------+------+            |
                                   +-----+---------+-----------+-------------+---------------------+
                                         |         |           |             |
                          HTTPS/JSON    v         v           v             v
                          +------------------------------------------------------------------+
                          |                     BFF Layer (Python/FastAPI)                    |
                          |  +---------------+ +----------------+ +--------------------+      |
                          |  | Ingestion BFF | | Review BFF     | | Editor/Admin BFF   |      |
                          |  |   :8001       | |   :8002        | |   :8003            |      |
                          |  +-------+-------+ +--------+-------+ +----------+---------+      |
                          +----------+------------------+------------------- +-----------------+
                                     |                   |                    |
                                     v                   v                    v
                          +------------------------------------------------------------------+
                          |              Core Python API Services (FastAPI)                   |
                          |  +------------+ +-------------+ +-----------+ +------------+       |
                          |  | Source     | | Job/Pipeline| | Epic/Story| | Export     |       |
                          |  | Mgmt Svc   | | Control Svc | | Svc       | | Svc (Jira) |       |
                          |  +-----+------+ +------+------+ +-----+-----+ +-----+------+       |
                          +--------+---------------+--------------+-------------+---------------+
                                   |               |              |             |
                     +-------------+         +-----+        +-----+             |
                     v                       v              v                  v
              +-------------+      +--------------------+          +--------------------+
              |  CouchDB    |<-----+  MCP Gateway        |<---------+  Agent Orchestrator |
              |  Cluster    |      |  (FastMCP server)   |  tools   |  (Celery workers +  |
              |  (docs,     |      |  couchdb.*, jira.*, |  calls   |   Redis broker)     |
              |  views,     |      |  fs.*, kill.check   |          +---------+----------+
              |  attachments|      +---------------------+                    |
              +-------------+               ^                                 | agent calls (skills)
                     ^                      |                                 v
                     | audit writes         | mediated access only  +-----------------------+
              +------+---------+            |                        |  Agents (Python procs) |
              | Audit/Compliance|<-----------+                        |  - Ingestion/Chunk     |
              | Log Service     |                                     |  - COBOL Structural    |
              | (hash-chained,  |                                     |  - JCL Structural      |
              |  append-only)   |                                     |  - Recommendation      |
              +-----------------+                                     |  - Epic/Story Writer   |
                                                                       |  - Q&A/Drilldown (chat)|
                                                                       +----------+------------+
                                                                                  | every LLM call routed through:
                                                                                  v
                                                                       +-----------------------+
                                                                       |  Guardrails Service    |
                                                                       |  (NeMo Guardrails,     |
                                                                       |   FastAPI, own         |
                                                                       |   container)           |
                                                                       +----------+------------+
                                                                                  v
                                                                       +-----------------------+
                                                                       |  LiteLLM Proxy         |
                                                                       |  (LLM Gateway)         |
                                                                       +----------+------------+
                                                     +---------------------------+---------------------------+
                                                     v                           v                           v
                                          +-----------------+      +----------------------+       +------------------+
                                          | Commercial APIs |      | Self-hosted OSS      |       | Self-hosted OSS  |
                                          | Anthropic/OpenAI|      | (vLLM cluster,       |       | (Ollama, dev/small|
                                          | /Azure/Bedrock  |      |  GPU nodes)          |       |  models)         |
                                          +-----------------+      +----------------------+       +------------------+

        Cross-cutting (attached to every hop above):
        +--------------------------------------------------------------------------+
        |  Langfuse (traces every agent step + every LLM call, linked by            |
        |  job_run_id / trace_id)                                                   |
        |  Structured JSON logging (stdout -> log shipper) at every layer           |
        |  Kill-switch: control-plane flag in Redis + CouchDB, checked by every      |
        |  Celery task and every MCP tool call before proceeding                     |
        +--------------------------------------------------------------------------+
```

### Connection rules (enforced, not just conventions)

- Browser → BFFs → Core API services only. The browser never talks to CouchDB, the MCP gateway, or LiteLLM directly.
- Agents → MCP Gateway → CouchDB/external systems. Agents have no CouchDB driver and no direct HTTP client to Jira, etc., in their code — enforced by lint/code review and by network policy (agent containers have no egress except to the MCP gateway, Guardrails/LiteLLM, and Langfuse).
- Agents → Guardrails service → LiteLLM Proxy → model providers. Agents never call LiteLLM directly; the guardrails hop is mandatory in the network path.
- Core API services may call CouchDB directly (trusted first-party code, not agent/LLM-influenced), but all agent-produced data flows through MCP so every write is uniformly audited at one chokepoint.

### 1a. Mainframe SCM connector (source ingestion, second on-ramp)

Manual file upload (§2.2, `source_upload`) is one ingestion path; the other is pulling source directly from the client's mainframe source/change-management (SCM) tool, since COBOL/JCL/copybooks in a real engagement live there, not in a folder someone exports by hand.

**Tool coverage and access mechanism** (research summary; re-verify against the specific client's tool/version before implementation):

| Tool | Access mechanism | Maturity |
|---|---|---|
| Broadcom Endevor | REST API v2 (Endevor Web Services); also a Zowe CLI plugin and "Explorer for Endevor" extension | Best supported — recommended reference implementation |
| Micro Focus/Rocket ChangeMan ZMF | REST API Server (v8.1+), true REST endpoints | Well supported |
| BMC AMI DevX / ISPW (Compuware) | REST API via Compuware Enterprise Services (CES), token auth | Well supported |
| CA/Broadcom PanValet | No modern REST surface; read-only PAM API for browsing members, or batch-extract via `PAN#1` to a PDS | Limited — realistic path is extract-to-PDS, then read via z/OSMF (below) |
| Generic / any tool via raw data set | z/OSMF z/OS Files REST API (`zos-files`) — reads any data set/PDS member/USS file directly | Universal fallback |

**Design**: exposed as a new MCP tool, `mainframe.fetch_source`, sibling to `file.fetch_source`. One thin adapter per tool behind a common interface (`list_elements(system, subsystem, type)`, `get_source(element_id)`, `get_metadata(element_id)`); adapter selection is env-driven (`SCM_TOOL=endevor|changeman|zosmf`, plus per-tool host/port/auth-mode/credential-reference), consistent with this project's `.env`-everywhere rule — swapping a client's tool is a config change, not a code change. The tool is strictly read-only: no write/checkout-back operation is ever exposed to agents, matching the existing rule that agents never get raw, unmediated access to an external system.

**Auth**: mainframe REST layers sit behind the site's z/OS security manager (RACF/ACF2/Top Secret) via SAF. In order of preference: (1) token-based auth via the Zowe API Mediation Layer, (2) client-certificate/mTLS bound to a low-privilege read-only service userid, (3) basic auth over TLS only, least preferred. Credentials are referenced (not inlined) from `.env`, same pattern as the LiteLLM API keys in §4.

**Data model reuse**: a connector pull produces the same `source_upload` → `source_file` → `chunk` shape as a manual upload (§2.2), not a parallel schema — see the added fields there. It goes through the same `secret_scan_result` gate before `status: ready_for_pipeline`, since mainframe source can carry embedded credentials/PII same as an upload, and feeds the existing `ingestion-chunking` skill unchanged.

**Audit**: every mainframe read is logged via the existing `audit.append` tool / `audit_event` type (§6.2) — requesting agent, credential-reference used, element identifier retrieved, timestamp, result — no new audit mechanism, just new event fields on the existing shape.

### 1b. Issue tracker export adapter (backlog export, second off-ramp)

Once epics/stories exist (§2.2), a reviewer exports selected items to a backlog tool via the Editor MFE (§8). Sibling design to §1a's mainframe connector: one thin adapter per tool behind a common `IssueTrackerAdapter` interface (`validate_connection`, `list_repos_or_projects`, `export_stories`), a flat registry, and a factory function — adapters that aren't wired for a client fail loudly with `NotImplementedError` rather than silently faking success.

**Tool coverage**:

| Tool | Status | Protocol |
|---|---|---|
| GitHub | Real | REST Issues API (`api.github.com`) |
| Jira | Designed, not implemented | Jira Cloud REST API v3 (documented target; every method raises `NotImplementedError`) |

**Mapping (GitHub)**: Epic → GitHub Milestone, Story → GitHub Issue assigned to that milestone. Plain REST Issues API (`POST /repos/{owner}/{repo}/milestones`, `POST /repos/{owner}/{repo}/issues`) — not Projects v2's GraphQL API — since Milestones map 1:1 onto "Epic" without new auth scopes or a heavier API surface. Milestone creation is idempotent (matched by title against `GET .../milestones?state=all` before creating) to avoid duplicates on retry. Each issue's body embeds an "Acceptance Criteria" bullet list and a "Traceability" section listing `source_program_ids`, so the traceability requirement survives inside the exported artifact itself, not just in CouchDB.

**Auth**: `connection_config` carries a `credential_ref` (e.g. `env://GITHUB_PAT_ACME2026`), never a literal secret — the same reference-not-inline rule §1a's mainframe credentials follow. `GitHubAdapter` is the first adapter in this codebase that actually dereferences a credential into a live token (via `os.environ`), since the mainframe adapters never make real outbound HTTP calls; a real secrets manager is a later hardening step, not this pass's scope.

**Design**: exposed as a new MCP tool, `issue_tracker_export`, tool-discriminated (`tool: "github"|"jira"`) rather than one tool per tracker, since both share the same request/response shape (`epic_ids`, `story_ids`, `connection_config` in; `exported`/`failed`/`epic_milestones` out). One failed story doesn't abort the batch — per-story `try`/`except` routes failures (including GitHub rate-limit `403`/`429` responses) into the `failed` list with a reason. Successful writes are written back onto the `story`/`epic` documents (`export_status`, `export_target`, `external_issue_key`/`external_milestone_id`, `external_issue_url`/`external_milestone_url`) and each export is audited via `audit.append` (`event_category: "export"`), mirroring §1a's audit approach.

**UI**: the Editor MFE (§8) presents a destination picker (GitHub / Jira) with a real, fillable connection form for both. Selecting Jira and submitting surfaces the backend's `NotImplementedError` verbatim as a 501 — the same failure path already proven for real (non-mock) mainframe SCM tools in the Upload MFE.

## 2. CouchDB data model

### 2.1 Document type convention

CouchDB has no native collections, so documents are disambiguated by a `type` field plus views/Mango indexes. Databases are split by concern (not one giant database) for compaction, replication scoping, and access control:

| Database | Contains `type` values |
|---|---|
| `sources` | `source_upload`, `source_file`, `chunk` |
| `parsed_structure` | `cobol_program_structure`, `jcl_job_structure`, `copybook_structure` |
| `agent_runs` | `job_run`, `agent_task`, `agent_message` (chat/drilldown transcripts) |
| `recommendations` | `migration_recommendation`, `risk_assessment` |
| `backlog` | `epic`, `story`, `export_record` |
| `audit_log` | `audit_event` (append-only, see §6 — separate DB so replication/retention/ACL policy differs from the rest) |
| `config_meta` | `client_project`, `skill_version_snapshot`, `model_policy` |

Every document carries at minimum:

```json
{
  "_id": "...",
  "_rev": "...",
  "type": "cobol_program_structure",
  "schema_version": 1,
  "project_id": "client-acme-2026",
  "created_at": "2026-07-02T14:03:00Z",
  "created_by": "agent:cobol-structural-analyzer@v3 | user:bhakti.kundu@gmail.com",
  "updated_at": "...",
  "trace_id": "langfuse-trace-uuid"
}
```

`project_id` scopes data per client engagement. Recommended: partitioned databases keyed by `project_id` for `sources`, `parsed_structure`, `recommendations`, `backlog` (query/index scoping and easy per-client export/deletion at offboarding); `agent_runs` and `audit_log` stay unpartitioned since cross-project audit queries are a real compliance need.

### 2.2 Representative document shapes

**`source_upload`** (one per user upload batch, or one per mainframe connector pull — see `source_origin`):

```json
{
  "type": "source_upload", "project_id": "acme-2026",
  "uploaded_by": "user@client.com", "upload_batch_id": "uuid",
  "source_origin": "manual_upload|mainframe_scm",
  "file_count": 42, "total_bytes": 1834213,
  "status": "received|scanning|ready_for_pipeline|failed",
  "secret_scan_result": {"flagged_files": [], "scan_passed": true}
}
```

A mainframe connector pull sets `uploaded_by` to a connector identity (e.g. `connector:mainframe-endevor`) and `source_origin: "mainframe_scm"` rather than a human email, but is otherwise the same document — it goes through the same `secret_scan_result` gate and `status` lifecycle as a manual upload (§1a).

**`source_file`** (one per COBOL/JCL/copybook file):

```json
{
  "type": "source_file", "project_id": "acme-2026", "upload_batch_id": "uuid",
  "filename": "PAYROLL01.CBL", "language": "cobol|jcl|copybook",
  "sha256": "...", "line_count": 4820,
  "_attachments": {"source.txt": {"content_type": "text/plain", "stub": true, "length": 812233}},
  "chunking_required": true,
  "source_origin": "manual_upload|mainframe_scm",
  "scm_element_ref": null
}
```

When `source_origin` is `mainframe_scm`, `scm_element_ref` is populated for traceability back to the mainframe system of record, e.g. `{"tool": "endevor", "system": "PAYSYS", "subsystem": "PAYROLL", "type": "COBOL", "element_id": "PAYROLL01", "version": "12"}`.

Raw source is stored as a CouchDB attachment, not inlined in the JSON body, so documents stay small and views/replication can skip large payloads when not needed.

**`chunk`** (produced by the ingestion agent when a file exceeds context-window budget):

```json
{
  "type": "chunk", "project_id": "acme-2026", "source_file_id": "...",
  "chunk_index": 3, "of_chunks": 7, "chunk_strategy": "paragraph-boundary",
  "overlap_lines": 15, "start_line": 601, "end_line": 900
}
```

**`cobol_program_structure`** (LLM-native extraction result):

```json
{
  "type": "cobol_program_structure", "project_id": "acme-2026", "source_file_id": "...",
  "program_id": "PAYROLL01",
  "divisions": {"identification": {}, "environment": {}, "data": {}, "procedure": {}},
  "copybooks_referenced": ["EMPMASTR", "PAYRATES"],
  "paragraphs": [{"name": "1000-MAIN", "calls": ["2000-CALC-GROSS"], "performs": []}],
  "call_graph": {"nodes": [], "edges": [], "confidence": 0.82},
  "external_calls": [{"target": "SUBRTN99", "call_type": "CALL", "resolved": false}],
  "extraction_method": "llm_native_chunked", "chunks_used": 7,
  "self_check_pass": {"performed": true, "discrepancies_found": 2, "resolved": true},
  "confidence_score": 0.82,
  "needs_human_review": true
}
```

**`jcl_job_structure`**:

```json
{
  "type": "jcl_job_structure", "project_id": "acme-2026", "source_file_id": "...",
  "job_name": "PAYRUN01",
  "steps": [{"step_name": "STEP010", "exec_pgm": "PAYROLL01", "cond_codes": ["COND=(4,LT)"],
             "dd_statements": [{"ddname": "SYSIN", "dsn": "PAY.INPUT.FILE"}]}],
  "step_dependency_graph": {"edges": [{"from": "STEP010", "to": "STEP020", "condition": "RC<=4"}]},
  "procs_referenced": ["PROCLIB01"],
  "schedule_hint_detected": "daily 02:00 (inferred from naming/comments)",
  "confidence_score": 0.9
}
```

**`migration_recommendation`**:

```json
{
  "type": "migration_recommendation", "project_id": "acme-2026",
  "subject_type": "cobol_program|jcl_job", "subject_id": "...",
  "recommended_target": "java_spring_boot|python_microservice|python_airflow_dag|python_cron_script",
  "rationale": "text...", "confidence_score": 0.75,
  "decision_factors": {"complexity": "high", "state_management": "heavy", "batch_vs_online": "online",
                        "performance_sensitivity": "high", "integration_points": 6},
  "alternative_considered": {"target": "python_microservice", "why_rejected": "..."},
  "risk_flags": ["undocumented external CALL to SUBRTN99"],
  "produced_by_agent": "recommendation-agent@v2", "produced_by_model": "claude-sonnet-4-5",
  "human_review_status": "pending|approved|rejected|edited",
  "reviewed_by": null, "reviewed_at": null
}
```

**`epic`** / **`story`** (see §1b for the export fields):

```json
{
  "type": "epic", "project_id": "acme-2026",
  "title": "Extract payroll gross-pay calculation",
  "description": "...",
  "export_target": "github|jira|null",
  "external_milestone_id": null, "external_milestone_url": null
}
```

```json
{
  "type": "story", "project_id": "acme-2026", "epic_id": "epic-uuid",
  "title": "Extract payroll gross-pay calculation into Python microservice",
  "description": "...", "acceptance_criteria": ["..."],
  "source_program_ids": ["PAYROLL01"],
  "generated_by_agent": "epic-story-writer@v1", "edited_by_human": true,
  "edit_history_ref": ["audit_log doc ids..."],
  "export_status": "not_exported|exported", "export_target": "github|jira|null",
  "external_issue_key": null, "external_issue_url": null
}
```

**`job_run`** / **`agent_task`** (pipeline execution tracking — mirrors Celery state durably):

```json
{
  "type": "job_run", "project_id": "acme-2026", "job_run_id": "uuid",
  "pipeline": "cobol_migration_analysis", "status": "running|completed|failed|killed",
  "started_at": "...", "finished_at": null,
  "tasks": [{"agent_task_id": "...", "agent": "ingestion", "status": "completed"},
            {"agent_task_id": "...", "agent": "cobol_structural", "status": "running"}],
  "kill_requested": false, "kill_requested_by": null, "kill_requested_at": null
}
```

**`audit_event`** — see §6.2 for the full shape.

### 2.3 Indexing and view strategy

- Prefer **Mango indexes** (`POST /db/_find`) for anything ad hoc/UI-driven (review queue filters, search-by-program-name) — this is a document-heavy, query-varied workload, not a heavy aggregation workload.
- Use classic **map/reduce views** only for genuinely aggregate needs: counts of programs by recommended target (dashboard tiles), counts of pending-review items per project, epic/story counts per project.
- Recommended Mango indexes:
  - `{"project_id": "asc", "type": "asc", "human_review_status": "asc"}` — the review queue's primary index.
  - `{"project_id": "asc", "type": "asc", "created_at": "desc"}` — recency-sorted lists (range queries on `created_at`, not skip-based pagination, for stable results at scale).
  - `{"source_file_id": "asc"}` on `parsed_structure` and `recommendations` — drilldown from a program to its derived artifacts.
  - `{"job_run_id": "asc", "started_at": "asc"}` on `agent_runs` — pipeline timeline reconstruction.
- **Partitioned databases** (`project_id` as partition key) let partition-scoped Mango queries skip irrelevant shards entirely — the single biggest cost/latency lever, since almost every UI query is naturally scoped to one client project.
- The **`_changes` feed** (with `since` + `filter` on `type`/`project_id`) drives: (a) near-real-time review-queue UI updates without polling, (b) audit-log append-only projections, (c) export-eligibility checks. This avoids building a separate event bus for intra-CouchDB reactivity.
- Attachments (raw source, large LLM transcripts) stay out of indexed fields, kept as `_attachments`, so index build/compaction stays cheap.

## 3. Agent pipeline design

### 3.1 Why Celery + Redis over Airflow/Temporal

Airflow is also a migration *target* in this product (JCL → Airflow DAGs), so using Airflow to run our own harness pipeline would be confusing in docs/support and adds a heavyweight scheduler (webserver, scheduler, metadata DB) for what is fundamentally a per-upload, on-demand DAG of ~5–8 tasks, not a cron-scheduled recurring DAG. Temporal is powerful for long-running durable workflows but is a heavier operational dependency (its own server + Postgres/Cassandra) than actually needed here (task retries, chaining, a kill switch, moderate concurrency). Celery+Redis is lightweight, Python-native, has mature retry/backoff/rate-limit primitives, and makes a kill-flag check inside a task loop trivial.

Trade-off acknowledged: Celery is weaker than Temporal at workflow-as-code with automatic replay after a crash. This is mitigated by persisting all intermediate state to CouchDB after each task (§3.3), so a crashed pipeline resumes from the last completed task rather than relying on Celery/Redis durability alone.

### 3.2 Pipeline stages (one Celery chain/chord per upload batch)

```
source_upload
   |
   v
[1] Ingestion & Chunking Agent
   - secret/PII scan (regex + LLM classifier) on raw source
   - splits large files into `chunk` docs (paragraph/PROC boundary aware, with overlap)
   - classifies each file: cobol_program | copybook | jcl_job | proc
   - writes source_file/chunk docs via MCP
   |
   +--------------> (fan-out per file, Celery group)
   v                                      v
[2a] COBOL Structural Agent        [2b] JCL Structural Agent
   - per chunk: extract divisions,      - extract steps, DD statements,
     paragraphs, call graph, data          COND/RC logic, PROC expansion
     items                               - build step dependency graph
   - merge-across-chunks pass            - infer schedule cadence from
     (stitches call graph, resolves        naming/comments (heuristic,
     cross-chunk references)                flagged as inferred not fact)
   - SELF-CHECK PASS: re-prompt with     - SELF-CHECK PASS similarly
     the assembled structure + original
     text, ask the model to find
     inconsistencies/omissions
   - confidence_score computed from
     self-check discrepancy count +
     chunk-count (more chunks = lower
     confidence, since cross-chunk
     stitching is the highest-risk step)
   - writes cobol_program_structure /
     jcl_job_structure via MCP
   |                                      |
   +---------------+----------------------+
                   v
        [3] Migration-Strategy / Recommendation Agent
           - reads parsed_structure + copybook fan-in/out via MCP
           - reasons per-program: microservice-in-Python vs
             Java Spring Boot (COBOL) or cron-script vs Airflow DAG (JCL)
           - decision factors prompted explicitly: statefulness,
             transaction boundaries, external system calls,
             batch-window/latency sensitivity, team's existing
             skillset (client-supplied metadata), volume/throughput
             signals from JCL step frequency
           - MUST produce rationale + at least one alternative considered
             + explicit risk_flags list (guardrail-enforced output schema)
           - writes migration_recommendation via MCP
                   |
                   v
        [4] Epic/Story-Writer Agent
           - groups recommendations into epics (e.g. by subsystem/
             copybook-sharing cluster, detected via call-graph
             connected-components, not per-file 1:1)
           - drafts stories with acceptance criteria referencing
             specific COBOL paragraphs/JCL steps as traceability
           - writes epic/story docs (human_review pending) via MCP
                   |
                   v
        job_run marked "completed" -> review queue populated
```

Each numbered stage is one `agent_task` document plus one Celery task; stage 2 is a Celery group (parallel fan-out per file) followed by a chord callback that only proceeds to stage 3 once every file in the batch is structurally parsed (or individually marked failed/needs-review, so one bad file doesn't block the whole batch).

### 3.3 State handoff and crash-resume

After every task, the agent's last action before returning is an MCP-mediated checkpoint write into `job_run.tasks[i]`. On worker restart, a reconciler task (run at Celery worker startup and via periodic beat every 5 minutes) scans `agent_runs` for `job_run` docs with `status: running` but no live Celery task heartbeat, and re-enqueues from the last completed stage rather than restarting the whole batch — the compensating control for not using Temporal's built-in replay.

### 3.4 Confidence scoring and human-in-the-loop for LLM-native parsing limits

Because this system deliberately doesn't build an AST-based parser, every structural-extraction and recommendation document carries a `confidence_score` and `needs_human_review` boolean, computed from: chunk count (more chunks → more stitching risk), self-check-pass discrepancy count, and presence of unresolved external calls/copybooks. The review-queue UI (§8) sorts/filters by this score so humans triage low-confidence items first rather than the system silently presenting LLM output as ground truth.

**Upgrade path**: if confidence scores prove unreliable in practice, a static-analysis pass (e.g. an ANTLR COBOL/JCL grammar) can be added as another MCP tool (`static_parse.cobol`) whose output is compared against the LLM extraction in the self-check pass. This is additive, not a rewrite — `parsed_structure` documents already carry an `extraction_method` field, so a hybrid method is just a new value for that field.

### 3.5 Skills folder convention

```
agents/
  skills/
    cobol-structural-analysis/SKILL.md
    jcl-structural-analysis/SKILL.md
    migration-recommendation/SKILL.md
    epic-story-writer/SKILL.md
    ingestion-chunking/SKILL.md
    mainframe-ingestion/SKILL.md
    qa-drilldown/SKILL.md
  tools/                      # MCP tool declarations/schemas the skills are allowed to call
    couchdb_tools.md
    jira_export_tool.md
    mainframe_tools.md
```

`mainframe-ingestion/SKILL.md` describes how/when to trigger a connector-based pull (e.g. "pull all elements in system X, subsystem Y matching type COBOL") versus a manual upload — deliberately editable by a non-engineer (a client's COBOL SME knows which systems/subsystems matter, not the harness team), same rationale as every other skill file below. `agents/tools/mainframe_tools.md` documents the `mainframe.fetch_source` schema (§1a) alongside the existing tool declarations.

Each `SKILL.md` is markdown (prompt template, guidance, output-schema description, examples) editable by non-engineers — e.g. a client's COBOL SME correcting how the recommendation agent weighs factors — without touching Python. The agent runtime loads the skill file at task start and records its content hash into `agent_task.skill_version_hash`, so every recommendation is traceable to the exact skill wording that produced it (required for the audit trail, §6). Skill files are versioned in git; a `config_meta`/`skill_version_snapshot` document captures which skill hash was active per `job_run` for reproducibility.

### 3.6 Secondary feature: chat/drilldown

A lightweight, separate FastAPI endpoint plus a `qa-drilldown` skill lets a reviewer ask a follow-up question about one already-parsed program ("why did you recommend Java here?"). This runs synchronously (not through Celery), still goes through Guardrails → LiteLLM, and is still logged to Langfuse and the audit log — but it's explicitly outside the main pipeline: it reads existing `parsed_structure`/`recommendation` docs via MCP as context and does not write new recommendation/epic documents (it may write an `agent_message` transcript doc for audit purposes). Kept intentionally thin and secondary, per the product's async-review-queue-first interaction model.

## 4. LLM gateway (LiteLLM) integration

- **Deployment**: LiteLLM Proxy runs as its own container (`litellm-proxy`, pinned image tag — never `:main`), reachable only internally. Config via a mounted `litellm_config.yaml` plus `.env`-sourced secrets — API keys are never in the YAML directly; the YAML references `os.environ/ANTHROPIC_API_KEY` etc., consistent with this project's `.env`-everywhere rule.
- **Model registry** (`litellm_config.yaml`, illustrative):

```yaml
model_list:
  - model_name: cobol-analysis-default
    litellm_params: {model: anthropic/claude-sonnet-4-5, api_key: os.environ/ANTHROPIC_API_KEY}
  - model_name: cobol-analysis-oss
    litellm_params: {model: openai/llama-3.3-70b, api_base: http://vllm-cluster:8000/v1, api_key: os.environ/VLLM_API_KEY}
  - model_name: cobol-analysis-dev
    litellm_params: {model: ollama/qwen2.5-coder:32b, api_base: http://ollama:11434}
  - model_name: commercial-gpt
    litellm_params: {model: openai/gpt-5.1, api_key: os.environ/OPENAI_API_KEY}
router_settings:
  routing_strategy: usage-based-routing-v2
  fallbacks: [{"cobol-analysis-default": ["cobol-analysis-oss"]}]
litellm_settings:
  success_callback: ["langfuse"]
  failure_callback: ["langfuse"]
```

- **Model selection by agents**: each skill's frontmatter (or a `model_policy` CouchDB document, per project) specifies a logical model name (e.g. `cobol-analysis-default`), never a literal provider/model string. A `model_policy` document per `project_id` lets an admin route a specific client's traffic to OSS-only models (data-residency requirement) by changing the mapping in CouchDB — no agent code or skill markdown changes needed.
- **Side-by-side OSS + commercial**: LiteLLM treats a self-hosted vLLM/Ollama endpoint identically to a commercial provider in its `model_list`; router-level fallback chains (commercial → self-hosted, or the reverse for confidentiality-first policies) and per-model rate limits/budgets are configured once at the gateway, not per agent.
- **Langfuse wiring**: LiteLLM has native Langfuse success/failure callbacks (shown above) — every model call auto-emits a Langfuse generation event tagged with `trace_id` propagated from the agent (`trace_id = job_run_id + agent_task_id`, so all LLM calls within one pipeline task nest under one trace).

## 5. Guardrails integration (NeMo Guardrails)

- Runs as its own containerized FastAPI service (`nemoguardrails server`), not embedded in each agent process, so guardrail policy (colang rails + yaml config) can be updated/redeployed independently and owned by a security/compliance team separately from agent/skill authors.
- **Placement in the request path**: an agent's LLM client points at the Guardrails service's OpenAI-compatible endpoint, not LiteLLM directly. Guardrails internally forwards to LiteLLM as its configured "LLM engine." The path is always: `agent → guardrails (input rail) → LiteLLM → model provider → guardrails (output rail) → agent`.
- **Input rails**: jailbreak/prompt-injection detection — relevant because COBOL source itself is untrusted input; an adversarial comment embedded in source could attempt prompt injection against the analysis agent, a risk fairly specific to this product. Also PII/secret leakage screening on the outbound prompt, as defense-in-depth alongside the ingestion agent's own secret-scan pass.
- **Dialog/execution rails**: constrain agents to their declared skill's intent (e.g. the recommendation agent's rail config prevents it from being steered into unrelated tasks via injected text in source comments).
- **Output rails**: schema/format validation of agent output (does the recommendation JSON have required fields: `rationale`, `alternative_considered`, `risk_flags` — reject/retry with a corrective prompt if not, before the doc ever reaches CouchDB); a fact-check/self-consistency rail for the COBOL structural agent's self-check pass, checked against the original source chunk as ground truth.
- Guardrail pass/fail/rail-triggered events are logged to both Langfuse (as a span) and the audit log (as an `audit_event` of type `guardrail_decision`) — a rejected/retried output is compliance-relevant, since it shows the system caught and corrected a bad output before it reached a human.

## 6. Observability and audit/compliance design

### 6.1 Langfuse — operational tracing, not the compliance record of truth

- Self-hosted Langfuse (Postgres + ClickHouse + Langfuse server containers, per Langfuse's standard self-host topology). Self-hosting is necessary here regardless, since source code and prompts must not leave the client's environment via a third-party SaaS trace store.
- Every agent task opens one Langfuse trace (`trace_id = job_run_id:agent_task_id`); every LLM call is a nested generation span (automatic via the LiteLLM callback, §4); every guardrail check and every MCP tool call is a nested span.
- Langfuse is optimized for debugging/quality/cost (token usage, latency, prompt/response inspection, eval scores). It is explicitly *not* the immutable compliance ledger — Langfuse data is mutable/deletable by design, and its retention model targets engineering observability, not legal recordkeeping.

### 6.2 Audit log — the compliance record of truth

A separate `audit_log` CouchDB database, written to exclusively through the MCP gateway's `audit.append` tool (application code and agents never write to it any other way), with one `audit_event` per every recommendation-affecting action:

```json
{
  "type": "audit_event", "event_id": "uuid",
  "event_category": "agent_output|human_review_decision|guardrail_decision|export|kill_switch|config_change",
  "project_id": "acme-2026",
  "actor": {"kind": "agent|user|system", "id": "recommendation-agent@v2 | bhakti.kundu@gmail.com"},
  "action": "created_recommendation", "subject_doc_id": "...", "subject_doc_rev": "...",
  "before_state_hash": "sha256(prev doc)", "after_state_hash": "sha256(new doc)",
  "model_used": "claude-sonnet-4-5", "skill_version_hash": "sha256(SKILL.md content)",
  "timestamp": "2026-07-02T14:03:00.421Z",
  "prev_event_hash": "sha256 of previous audit_event in this project's chain",
  "this_event_hash": "sha256(canonicalized event content + prev_event_hash)"
}
```

Design choices that satisfy the SEC 17a-4 "audit-trail alternative" (chosen over literal WORM hardware, per the 2023 amendment allowing either approach — see §0 risk #1):

- **Hash chaining** (`prev_event_hash`/`this_event_hash`) makes tampering detectable: altering any past event breaks the chain for every subsequent event. A periodic job publishes the current chain-tip hash to an external, independent anchor (e.g. a write-once S3 bucket with Object Lock in Compliance mode, or a public timestamping service), so even a compromised CouchDB admin can't quietly rewrite history without the anchor mismatching.
- **Append-only enforcement at the application layer**: the MCP `audit.append` tool only supports create, never update/delete. A CouchDB `validate_doc_update` function additionally rejects any update/delete attempt on `audit_log` documents server-side, so even a direct API caller bypassing MCP is blocked by the database itself — defense in depth.
- **Complete traceability of who/what/when for every recommendation**: every `migration_recommendation`/`epic`/`story` document's lifecycle (created by agent, viewed, edited, approved/rejected by which named human user, exported to Jira) has a corresponding `audit_event`.
- **Retention**: default 7 years (placeholder, flagged in §0 risk #1 for legal confirmation; 17a-4 itself sets a 3-year floor for many broker-dealer records, longer for partnership/membership records, and bank regulatory retention expectations often run longer). Enforced by disabling CouchDB compaction/purge on `audit_log` and by the external anchor's own retention-lock policy.
- **Exportability**: 17a-4 requires firms to furnish records "in a reasonably usable electronic format" on request — the audit service exposes an `audit.export_range` tool producing a signed, chain-verifiable JSON/CSV bundle for a date range/project, usable for a client's own regulator production requests.
- This differs from ordinary application logging (which is about debugging/operations, can be sampled, rotated, and deleted per normal retention policy) precisely in: immutability enforcement, cryptographic tamper-evidence, indefinite/regulatory-length retention, and being scoped to recommendation-affecting actions rather than every log line.

### 6.3 Structured logging (ordinary, every layer)

Every Python service/agent/BFF emits JSON-structured logs (`structlog` recommended) to stdout, shipped by the container runtime's log driver to a central store (e.g. ELK/OpenSearch or a cloud-native equivalent) with normal rotation/retention (30–90 days is typical — a distinctly shorter lifecycle than the audit log). Every exception is caught at each layer boundary (BFF request handler, API service, agent task, MCP tool call) and logged with `trace_id` correlation to Langfuse; if the exception occurred during a recommendation-affecting action, it also emits an `audit_event` of category `agent_output` with an `error` field rather than silently failing.

## 7. Emergency kill-switch design

- **Control surface**: a protected endpoint on the Job/Pipeline Control Service, e.g. `POST /admin/kill {scope: "all" | "project:<id>" | "job_run:<id>"}`, restricted to an admin role, itself audit-logged (`event_category: kill_switch`).
- **Mechanism**: sets a flag in two places simultaneously for redundancy — (1) a Redis key (`kill:global`, `kill:project:<id>`, `kill:job:<id>`) for fast in-memory checks, and (2) `job_run.kill_requested = true` in CouchDB for durability/audit (Redis alone isn't acceptable as the sole source since it's not the compliance record and could be flushed).
- **How in-flight tasks respond**: every Celery task checks the kill flag at the start of each unit of work (before each LLM call, before each MCP tool call, and inside the chunk-processing loop for long tasks) via a shared helper (`kill_switch.check(project_id, job_run_id)`) — Redis first for speed, falling back to a CouchDB read if Redis is unreachable, fail-safe (if uncertain, treat as killed, not "keep running"). On a positive check, the task raises a controlled `AgentKilled` exception, marks itself `status: killed` in its `agent_task` doc, and does not proceed to write further recommendation/epic documents. Partial output already written stays visible to reviewers, tagged with `job_run.status: killed` so the UI clearly marks it as incomplete rather than a normal completed result.
- **Global kill** (`scope: all`) additionally revokes all queued-but-not-yet-started Celery tasks (`celery.control.revoke` with `terminate=True` for anything already dispatched to a worker), so nothing new starts even before the per-task flag check would catch it — belt-and-suspenders, since revoke alone can race with a task that already grabbed work.
- **Guardrails/LiteLLM layer also honors kill**: the guardrails service checks the same kill flag (passed as a request header/claim from the agent) before forwarding to LiteLLM — this stops an in-progress long LLM generation from being used even if the agent process itself is slow to notice the flag, cutting cost/exposure faster than waiting for the agent's own polling interval.
- **UI**: the Admin/Observability micro frontend (§8) exposes a prominent, confirmation-gated "Kill all agents" button and per-job-run kill buttons in the review dashboard, both calling the same endpoint.

## 8. Frontend micro frontend topology

Each micro frontend is its own Vite+React app, its own port, its own repo folder, independently deployable/buildable/testable:

| MFE | Port | Purpose | Backed by |
|---|---|---|---|
| Shell (host) | 3000 | Auth/session, top nav, runtime-composes remotes via Module Federation, global error boundaries per remote | Thin, mostly static; talks to an Auth BFF for session |
| Upload/Ingestion | 3001 | Upload COBOL/JCL/copybook files, view secret-scan results, kick off pipeline run, see job progress | Ingestion BFF :8001 |
| Review Queue / Dashboard | 3002 | Primary surface: sortable/filterable list of parsed programs, recommendations, confidence scores, approve/reject/comment; expand a row for source/recommendation/backlog detail; trigger epic/story generation | Review BFF :8002 |
| Epic/Story Editor | 3003 | Edit generated epics/stories, view traceability back to source paragraphs/JCL steps, export to GitHub (Milestones/Issues, real) or Jira (real UI, backend not implemented — see §1b) | Editor/Admin BFF :8003 (export sub-path) |
| Admin/Observability | 3004 | Kill switch, job_run history, model policy per project, links out to Langfuse UI, audit log viewer/export | Editor/Admin BFF :8003 |

**Composition mechanism**: Module Federation 2.0 (via `@module-federation/vite` or an rspack MF plugin — Vite-based tooling recommended for faster local dev over classic webpack MF). The shell app dynamically imports each remote's exposed root component at runtime (not iframe-embedded), each remote wrapped in its own React error boundary in the shell. This is how failure isolation works: if the Epic/Story Editor remote fails to load (network error, remote down, runtime exception), the shell's error boundary for that specific mount point shows a "this section is temporarily unavailable" fallback while Upload, Review Queue, and Admin remain fully functional — each remote is a separately fetched bundle and separately rendered subtree, so a crash in one doesn't unmount the others.

**Shared dependencies governance** (§0 risk #5): React, React-DOM, and a shared design-system/component-library package are declared as Module Federation "shared singletons" with a pinned semver range. A lightweight internal package (`@harness/shared-deps`) pins the exact versions all MFE teams build against, checked in CI (a version-drift check step) before any MFE is allowed to deploy — this is a process control, not purely a technical one, since MF's biggest real-world failure mode is silent runtime incompatibility from independently-upgraded shared deps.

**BFFs** (Python FastAPI, one per user journey) exist specifically where a page needs aggregation across multiple core API services — e.g. the Review Queue page needs parsed-structure summary + recommendation + human-review-status + job-run-progress in one payload, so its BFF fans out to the Source Mgmt, Job/Pipeline Control, and Epic/Story services concurrently (`asyncio.gather`) and shapes one response tailored to that page, rather than the React app making 3–4 separate round trips — this is also a direct lever for the <5s NFR (§9).

## 9. NFR satisfaction strategy

### 9.1 <5 second end-to-end React response time

- **Async-first UI, no blocking calls on the hot path**: uploading source or triggering a pipeline run returns immediately (a 202-style "job accepted" response with a `job_run_id`); the UI polls (or subscribes via a lightweight SSE/WebSocket endpoint on the BFF, backed by the CouchDB `_changes` feed) for status. The multi-minute LLM pipeline is never in the request/response path the 5-second budget applies to — that budget covers page loads, dashboard queries, and interactive actions (approve/reject/edit a recommendation), all fast CouchDB reads/writes.
- **BFF-level response shaping and concurrent fan-out** (§8) avoids serial waterfalls of API calls from the browser.
- **Caching**: a Redis-backed cache (the same Redis used as the Celery broker, a separate logical DB index) in front of expensive/frequently-reused reads: dashboard aggregate counts (map/reduce view results), skill-file content (read on every agent task start — cached with a TTL plus a git-commit-hash cache-busting key), `model_policy` lookups, and rendered epic/story lists for the editor. Cache invalidation is keyed off the CouchDB `_changes` feed (a small cache-invalidation subscriber process) rather than a blind TTL alone, to avoid staleness after an edit/approval.
- **Pagination**: all list endpoints (review queue, epic/story lists) use range-based pagination on indexed fields (`created_at`/`confidence_score` startkey/limit), never unbounded `_all_docs` scans.
- **Frontend bundle performance**: Module Federation remotes are code-split and lazy-loaded per route so the shell's initial load isn't paying for every MFE's JS upfront.

### 9.2 <1% error rate

- **Validation boundaries** at every layer: BFFs validate request shape (Pydantic models) before calling core services; core services validate before writing to CouchDB (Pydantic models mirroring the document schemas in §2); the guardrails output rail validates agent JSON against the expected schema before it's accepted, retrying with a corrective re-prompt (bounded retry count) rather than passing malformed data downstream.
- **Retries with backoff**: LiteLLM's built-in retry/fallback (§4) for transient provider errors/rate limits; Celery task-level `autoretry_for` with exponential backoff for MCP/CouchDB transient failures; idempotent writes (documents keyed so a retried task overwrites the same logical doc rather than duplicating) to make retries safe.
- **Circuit breakers**: the LiteLLM proxy has provider-level circuit breaking/cooldown built in; the MCP gateway wraps its CouchDB client calls with a circuit breaker (e.g. `pybreaker`) so a CouchDB blip doesn't pile up timeouts across every concurrent agent task.
- **Partial-failure isolation in pipelines**: the Celery group/chord fan-out per file (§3.2) means one malformed COBOL file failing structural analysis doesn't fail the whole batch — it's marked `needs_human_review` with the error captured, and the rest of the batch proceeds.
- **Guardrail-enforced schema compliance** is a correctness gate specifically for the "agent produced garbage" failure mode, the dominant realistic error source in an LLM-native-parsing system, as distinct from classic 5xx/network errors already covered by retry/circuit-breaker patterns.

## 10. Deployment topology

Container-per-service, one port per micro frontend (hard requirement). Docker Compose for local/dev; Kubernetes for staging/prod (recommended — consistent with "independently deployable" and gives per-service scaling, e.g. scaling Celery workers or vLLM GPU nodes independently of the BFFs).

| Component | Packaging | Self-hosted / managed |
|---|---|---|
| Shell + 4 MFEs | 5 separate containers, ports 3000–3004, static asset serving (nginx or Vite preview) | Self-hosted; could later move to a CDN per MFE for static assets |
| BFFs (3) + core API services (4) | Separate FastAPI containers, internal ports 8001–8003 (BFF) / 800x (core), behind an internal reverse proxy (nginx or Traefik) that terminates TLS and is the only externally reachable ingress for the browser | Self-hosted |
| CouchDB | 3-node CouchDB cluster (HA plus `_changes`-feed-driven replication) | Self-hosted initially; IBM Cloudant (managed CouchDB-compatible) is a documented drop-in upgrade path since the `ibmcloudant` SDK already targets both |
| Redis | Single instance (broker + result backend + cache); consider Redis Sentinel/Cluster for prod HA | Self-hosted or managed |
| Celery workers | Separate deployment from the API services, horizontally scalable, one worker pool per queue (`ingestion`, `structural`, `recommendation`, `epic_story`) so a slow queue doesn't starve others | Self-hosted |
| MCP Gateway | Its own FastMCP container, internal-only network, the sole egress point agents have to CouchDB/Jira | Self-hosted |
| LiteLLM Proxy | Its own container, pinned version, internal-only | Self-hosted |
| Guardrails service | Its own container (`nemoguardrails server`), internal-only, sits in front of LiteLLM | Self-hosted |
| vLLM cluster (OSS models) | GPU-backed containers/nodes, scaled per model | Self-hosted (requires GPU infra) |
| Ollama (dev/small OSS models) | Lightweight container, CPU or small GPU | Self-hosted |
| Langfuse | Self-hosted stack (Postgres + ClickHouse + Langfuse server) | Self-hosted (confidentiality requirement, §6.1) |
| Audit anchor store | Object storage with Object Lock/Compliance mode (e.g. S3-compatible WORM) | Managed cloud object storage recommended — compliance-grade WORM is a solved problem there |
| Secrets/`.env` | `.env` files per service/component, never committed; in Kubernetes, promoted to Secrets/External Secrets Operator reading from a vault, still following the "no hardcoding, config separate from code" rule at the deployment layer | N/A |

## Next steps (not part of this design pass)

This document is architecture-only; no application source exists yet. When scaffolding begins, the priority files are:

- `.env.example` — documents every environment variable this design implies (CouchDB URL/creds, Redis URL, LiteLLM proxy URL/keys, Langfuse keys, Guardrails service URL, MCP gateway URL, kill-switch admin token, mainframe connector settings: `SCM_TOOL`, host/port, auth-mode, credential-reference — §1a).
- `agents/skills/*/SKILL.md` — the editable behavior surface; should exist before any agent Python code, since code loads these rather than embedding prompts.
- `litellm_config.yaml` — the model registry, the concrete artifact that fulfills "swap models without touching agent code."
- `docker-compose.yml` (or equivalent Kubernetes manifests) — enumerates every container/port in §10, making the topology explicit early.
