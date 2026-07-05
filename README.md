# COBOL/JCL Migration Harness

A harness that uses LLM agents to read COBOL and JCL source, reason about
it, and produce research, recommendations, epics, and stories to guide a
client's mainframe modernization program. It targets two migration paths:

1. **COBOL programs → microservices** in Python or Java Spring Boot, with a
   documented rationale per program (why that target, what was considered
   and rejected, and what risks a migration engineer should watch for).
2. **JCL jobs → Python scripts** schedulable via cron/shell or Apache
   Airflow.

The system does not migrate code automatically. It produces a
human-reviewable backlog (epics and stories with acceptance criteria
tied to specific COBOL paragraphs or JCL steps) that a migration team then
executes — every agent output sits behind a review queue and a full,
hash-chained audit trail before it's trusted.

## How it works

```
source (upload or mainframe pull)
  -> Ingestion & Chunking Agent      (secret/PII scan, chunk large files)
  -> Structural Agent                (COBOL: real | JCL: not wired, see below)
  -> Migration-Recommendation Agent  (target + rationale + risk flags)
  -> Review Queue (human approves/rejects each recommendation)
  -> Epic/Story-Writer Agent         (understand -> cluster -> draft backlog)
  -> Epic/Story Editor (human edits, then exports to GitHub/Jira)
```

Every stage is a Celery task that reads/writes CouchDB exclusively through
an MCP gateway (agents never hold a database driver directly), calls an LLM
through a LiteLLM proxy by a *logical* model name (never a literal
provider string, so swapping models is a config change, not a code change),
and validates its own output against a Pydantic schema before it's trusted
(a rejected/malformed response retries once, then fails loudly).

### Architecture at a glance

| Layer | Technology | Why |
|---|---|---|
| Frontend | React micro-frontends (Module Federation), one shell + 4 independently-deployable remotes | A failure in one remote (e.g. the Editor) never takes down Upload or Review |
| BFFs | Python (FastAPI) | Page-specific aggregation so each MFE gets one call, not N |
| Core services | Python (FastAPI) | Source management, job/pipeline control, recommendations, epics/stories |
| Agents | Python + Celery/Redis | One task per pipeline stage; skills are editable markdown, not code |
| Database | CouchDB | 7 databases: `sources`, `parsed_structure`, `agent_runs`, `recommendations`, `backlog`, `audit_log` (append-only), `config_meta` |
| LLM gateway | LiteLLM proxy | Agents reference a logical model name (`cobol-analysis-dev`); the proxy config maps that to a real provider |
| Agent↔system access | MCP gateway (FastMCP) | The *only* path from agent code to CouchDB, the audit log, kill-switch state, and mainframe connectors |
| Guardrails | In-process stub this pass (schema validation is real; containerized NeMo Guardrails input-rail is not) | See [Current status](#current-status-what-is-real-vs-stubbed) |
| Observability | Structured logs this pass (Langfuse spans are logged, not shipped to a real Langfuse server) | See [Current status](#current-status-what-is-real-vs-stubbed) |
| Emergency stop | Real kill-switch (Redis + CouchDB flags), checked by every task and every MCP tool call | `POST /admin/kill` |

Full design rationale lives in [`docs/architecture.md`](docs/architecture.md).
**Note**: that document's own header still says "architecture-only, no
application source exists yet" — that line is stale. Treat its data model,
pipeline design, and NFRs as ground truth; treat its "not yet built"
framing as out of date. [`docs/deferred_scope.md`](docs/deferred_scope.md)
is the accurate, current source for what's real vs. stubbed.

### Agent skills

Agent behavior lives as editable markdown under `agents/skills/*/SKILL.md`
— a domain expert can change prompt wording or guardrail thresholds
without touching Python code.

| Skill | What it does | Status |
|---|---|---|
| `ingestion-chunking` | Secret/PII scan, file-type classification, paragraph/PROC-aware chunking of large files | Real |
| `cobol-structural-analysis` | Extracts divisions, paragraphs, call graph, external calls, copybook refs; self-checks its own output; scores confidence | Real |
| `jcl-structural-analysis` | Extracts JCL step structure, DD statements, COND/RC logic, step dependencies | Written, **not wired** — see below |
| `migration-recommendation` | Recommends a target (`java_spring_boot` / `python_microservice` / `python_airflow_dag` / `python_cron_script`) with mandatory rationale, alternative considered, and risk flags | Real |
| `cobol-code-understanding` | Reads a program's source + structure and writes a plain-English, ≤600-word summary before any backlog drafting happens | Real |
| `epic-story-writer` | Clusters programs into epics by shared copybooks/call-graph edges (deterministic), then drafts stories with acceptance criteria citing real paragraph/step names | Real, triggered independently of the per-file pipeline |
| `qa-drilldown` | Answers a reviewer's free-text follow-up about an already-parsed program | Skill written, **no endpoint wired** |
| `mainframe-ingestion` | Pulls COBOL/JCL/copybook source from a client SCM tool into the same shape as a manual upload | Real end-to-end for the mock adapter only — see [Forward Deployed Engineer](#forward-deployed-engineer-connecting-this-to-a-real-mainframe-repository) |

## Getting started

```bash
cp .env.example .env        # every config value is read from .env; nothing is hardcoded
make up                     # docker-compose up -d — brings up all 21 services
make init-db                # creates the 7 CouchDB databases + indexes (couchdb must be up first)
```

Then open the shell UI at **http://localhost:3000**. With no API keys
configured, the LLM gateway (`cobol-analysis-dev`) talks to an in-repo mock
LLM server, so the full pipeline runs end-to-end with zero external
dependencies — good for a first look, not for real COBOL understanding
(see [Current status](#current-status-what-is-real-vs-stubbed)).

To point the pipeline at a real model instead of the mock, edit
`infra/litellm/litellm_config.yaml`'s `cobol-analysis-dev` entry to resolve
to a real provider (e.g. `anthropic/claude-sonnet-4-5`), set the matching
API key in `.env`, and recreate the proxy: `docker-compose up -d --force-recreate litellm-proxy`.

### Running tests

```bash
make test            # everything
make test-backend    # pytest across every backend/agents/orchestrator/mcp_gateway package
make test-frontend   # npm test across every frontend package
```

### Service map

| Service | Port |
|---|---|
| Shell (MFE host) | 3000 |
| Upload/Ingestion MFE | 3001 |
| Review Queue MFE | 3002 |
| Epic/Story Editor MFE | 3003 |
| Admin/Observability MFE | 3004 |
| Ingestion BFF | 8001 |
| Review BFF | 8002 |
| Editor/Admin BFF | 8003 |
| Source Mgmt Service | 8004 |
| Job/Pipeline Control Service | 8005 |
| Recommendation Service | 8006 |
| Epic/Story Service | 8007 |
| MCP Gateway | 7000 |
| LiteLLM Proxy | 4000 |
| Mock LLM server | 9000 |
| CouchDB | 5984 |
| Redis | 6379 |

## Current status: what is real vs. stubbed

This matters for anyone deciding what to build next. Read
[`docs/deferred_scope.md`](docs/deferred_scope.md) for the full, current
list; the highlights:

- **Real and wired**: ingestion/chunking, COBOL structural analysis,
  migration recommendation, the two-stage epic/story generation pipeline,
  the MCP gateway (every tool has tests), the audit log's hash-chained
  append-only design, the kill-switch, the Review Queue and Epic/Story
  Editor UIs, GitHub export.
- **Written but not wired**: JCL structural analysis (the skill and prompt
  exist; `agents/jcl_structural/task.py` marks itself `skipped` and never
  runs), the `qa-drilldown` skill (no FastAPI endpoint calls it yet).
- **Real seam, stub implementation**: mainframe connectivity (see the next
  section in detail), guardrails (schema validation is real; the
  containerized NeMo Guardrails input-rail service is not built —
  `agents/common/guardrails_client.py` is a local stand-in), Langfuse
  observability (spans are logged as structured logs, not shipped to a
  real Langfuse server).
- **Not implemented**: the audit log's external hash-chain anchor (e.g.
  publishing the chain tip to S3 Object Lock) — worth closing before this
  touches real regulated data, per the SEC/Treasury retention and
  traceability requirements this repo is designed around.

---

## Forward Deployed Engineer: connecting this to a real mainframe repository

This section is for the engineer who takes this repo on-site to a client
and needs it to read source from that client's *actual* mainframe SCM tool
instead of the fixture data every demo uses today. Read this before you
touch code — the seam you need is already built and tested; you should
not need to change the frontend, the MCP gateway's tool contract, or the
data model at all.

### What already works, and what you must build

Every non-mock code path is real, tested, and wired end-to-end **except
the one thing that's inherently client-specific: the wire protocol to the
client's actual SCM tool.** That gap is deliberate and fails loudly:
selecting `endevor`, `panvalet`, or `changeman` in the UI today returns a
clean HTTP 501 with a message naming exactly what's missing — it will
never silently fall back to mock/fixture data.

```
frontend: MainframeConnectForm.tsx (tool picker: endevor | panvalet | changeman | mock)
    -> POST /mainframe-pulls   (backend/source_mgmt_service/app/routes/mainframe_pulls.py)
    -> mcp.mainframe_fetch_source(...)   (MCP gateway tool call)
    -> mcp_gateway/app/tools/mainframe_tools.py
    -> agents/mainframe_ingestion/adapter.py :: get_adapter(tool)
    -> YOUR CODE GOES HERE: EndevorAdapter / PanvaletAdapter / ChangemanAdapter
```

Everything above "YOUR CODE GOES HERE" is implemented, tested, and does
not need to change. Below it, `_NotYetImplementedAdapter` intentionally
raises on every call:

```python
NotImplementedError(
    f"{self.tool_name} connector wire protocol not yet implemented "
    f"({self.protocol_description}); only the mock adapter is "
    f"available this pass. See docs/deferred_scope.md."
)
```

### Step by step

1. **Confirm which SCM tool the client actually uses**, and whether an
   adapter class already exists for it:
   - `EndevorAdapter` (`agents/mainframe_ingestion/adapter.py`) — target
     protocol: Endevor Web Services REST API v2.
   - `ChangemanAdapter` — target protocol: ChangeMan ZMF REST API Server
     (v8.1+).
   - `PanvaletAdapter` — target protocol: PAM API for browsing, or a
     batch-extract to a PDS read via z/OSMF.
   - If the client uses something else entirely (ISPW, a generic z/OSMF
     dataset browse, a plain SFTP/dataset extract), there is no stub for
     it yet — copy the shape of one of the three above as your starting
     point (see step 3).

2. **Get read-only credentials from the client's mainframe team before
   writing any code.** Per `docs/architecture.md` §1a, the preferred order
   is: (1) a Zowe API Mediation Layer token, (2) client-cert/mTLS to a
   low-privilege, read-only service ID, (3) basic auth over TLS only as a
   last resort. Whatever you get, you will reference it via a secret
   manager path, never a literal value — see step 4.

3. **Implement the adapter's three methods** in
   `agents/mainframe_ingestion/adapter.py`. The interface is fixed and
   already used correctly by every layer above it — implement exactly
   this shape (shown here for Endevor; the other two adapters take the
   same three methods):

   ```python
   class EndevorAdapter(MainframeAdapter):
       tool_name = "Endevor"
       protocol_description = "Endevor Web Services REST API v2"

       def list_elements(self, *, host, credential_ref, system, subsystem, element_type):
           # Call Endevor's REST API to list elements in this system/subsystem
           # matching element_type ("COBOL", "JCL", "COPYBOOK", ...). Return
           # [{"element_id": ..., "element_type": ..., "version": ...}, ...]
           ...

       def get_source(self, *, host, credential_ref, system, subsystem, element_type, element_id):
           # Fetch the raw source text for one element. Return it as a plain
           # str — the ingestion pipeline expects the same shape as a
           # manually-uploaded file's contents.
           ...

       def get_metadata(self, *, host, credential_ref, system, subsystem, element_type, element_id):
           # Return whatever the tool exposes as element metadata (version,
           # last-changed timestamp, etc.) as a dict — this becomes
           # scm_element_ref on the resulting source_file document.
           ...
   ```

   Do not change `MainframeAdapter`'s abstract interface, `get_adapter()`,
   `mainframe_tools.py`, `mainframe_pulls.py`, or the frontend form — they
   already handle any adapter that implements this interface correctly,
   including error propagation (any exception you raise surfaces to the
   UI as a real error message, not a silent failure).

4. **Resolve the credential reference inside your adapter, not before
   it.** `.env` holds only a reference, e.g.:

   ```
   MAINFRAME_ENDEVOR_HOST=your-endevor-host.client.example.com
   MAINFRAME_ENDEVOR_PORT=443
   MAINFRAME_ENDEVOR_AUTH_MODE=token
   MAINFRAME_ENDEVOR_CREDENTIAL_REF=vault://mainframe/endevor/readonly
   ```

   `credential_ref` arrives in your adapter method as that literal string
   (`vault://mainframe/endevor/readonly`) — add whatever secret-manager
   client the client's environment actually uses (Vault, AWS Secrets
   Manager, etc.) to dereference it into a real credential *inside* the
   adapter, at call time. Never log the resolved credential value; the
   audit event this call produces already logs `credential_ref` (the
   pointer) by design, never the secret itself.

5. **Switch the active tool** by setting `SCM_TOOL=<your-tool>` in `.env`
   (or just picking it in the UI's tool picker — both work; the env var
   only sets the form's default selection). Restart
   `source-mgmt-service` and `mcp-gateway`:

   ```bash
   docker-compose up -d --build source-mgmt-service mcp-gateway
   ```

6. **Test against the real system with a read-only, low-blast-radius
   call first** — use the UI's "List elements" button (`GET
   /mainframe-elements`) before "Pull selected" (`POST
   /mainframe-pulls`), since listing touches nothing but a directory/index
   call on the mainframe side. Confirm the response shape matches what
   `list_elements()` promises before wiring up a real pull.

7. **Add adapter-specific tests** alongside the existing ones in
   `agents/tests/test_mainframe_adapter.py` — that file already tests
   `MockAdapter` and confirms the not-yet-implemented adapters raise
   correctly; add your adapter's happy-path and error-path tests in the
   same style so `make test-backend` keeps covering it.

8. **Do not skip the audit trail.** Every real pull already flows through
   `mcp.audit_append(...)` with `event_category="agent_output"` and logs
   the element ID and credential *reference* used — this satisfies the
   same regulatory traceability requirement (SEC/Treasury retention rules)
   that governs every other agent output in this system. If your adapter
   needs additional client-specific audit fields (e.g. a change-control
   ticket ID from Endevor), add them to the `get_metadata()` return value
   — it flows straight into `scm_element_ref` on the resulting document,
   no schema change required.

### What NOT to do

- Don't make `EndevorAdapter`/etc. silently fall back to `MockAdapter` on
  connection failure — the existing fail-loud 501 behavior is intentional
  so a broken connector is never mistaken for a successful pull of real
  data.
- Don't bypass the MCP gateway to call the mainframe API directly from
  agent code — `agents/mainframe_ingestion/adapter.py` is called *through*
  `mcp_gateway/app/tools/mainframe_tools.py` specifically so every pull is
  audited the same way regardless of which tool sourced it.
- Don't put a literal credential in `.env`, a config file, or source code
  — `CREDENTIAL_REF` values are `vault://...`-style pointers by design;
  resolve them at call time from whatever secret manager the client
  environment provides.
- Don't widen the service account beyond read-only. This system only ever
  reads source for analysis; it does not write back to the mainframe.
