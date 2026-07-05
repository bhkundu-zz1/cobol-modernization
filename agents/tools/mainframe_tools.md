# MCP Tool: `mainframe.fetch_source`

Status: **REAL (mock adapter only)** — backs
`mcp_gateway/app/tools/mainframe_tools.py`, per architecture.md §1a and the
vertical-slice scope decision to make the mainframe SCM connector a real
second ingestion path this pass.

```
mainframe_fetch_source(
  tool: "endevor" | "panvalet" | "changeman" | "mock",
  host: str,
  credential_ref: str,      # a reference (e.g. "vault://mainframe/endevor/readonly"),
                             # NEVER a literal credential value
  system: str,
  subsystem: str,
  element_type: str,        # e.g. "COBOL"
  element_id: str | None = None,
) -> {"elements": [dict, ...]}                       # when element_id is None (listing)
   | {"source_text": str, "metadata": dict}           # when element_id is set (pulling)
```

- **Read-only, strictly**: no write/checkout-back operation is ever exposed
  to agents — this matches the existing rule that agents never get raw,
  unmediated access to an external system.
- `tool` selects the adapter implementation via the registry in
  `agents/mainframe_ingestion/adapter.py` (`SCM_TOOL` env var sets the
  default; the Upload MFE's tool picker can override per-call).
- **This pass's actual coverage**: `tool="mock"` is the only adapter with a
  real, runnable implementation — it returns fixture COBOL content
  (`fixtures/sample_cobol/PAYROLL01.CBL`) simulating a real element
  list/pull, so the full ingestion → structural → recommendation pipeline
  can be exercised end-to-end without a live mainframe. `tool="endevor"`,
  `"panvalet"`, and `"changeman"` select real adapter *classes* implementing
  the same interface (`list_elements`, `get_source`, `get_metadata`), but
  their HTTP calls raise `NotImplementedError` with a message naming the
  real wire protocol that's future work (Endevor REST API v2, ChangeMan ZMF
  REST API Server, PanValet PAM API / z/OSMF fallback — see
  architecture.md §1a's tool-coverage table and `docs/deferred_scope.md`).
  This must fail loudly and specifically, never silently return empty/mock
  data for a real tool selection.
- **Auth**: `credential_ref` is resolved server-side (gateway or adapter
  layer) against `.env`-configured credential storage — this tool's
  request/response never carries the literal credential.
- **Audit**: every call (list or pull) is logged via `audit.append`
  (`event_category: "agent_output"`) with the `credential_ref` used and the
  element identifier retrieved (never the credential itself) — no new audit
  mechanism, just new event fields on the existing shape, per
  architecture.md §1a.
- **Data model reuse**: a pull produces the same `source_upload` →
  `source_file` → `chunk` shape as a manual upload (see
  `backend/shared/models/source.py`), with `source_origin: "mainframe_scm"`
  and `scm_element_ref` populated — not a parallel schema. It goes through
  the same `secret_scan_result` gate before `status: ready_for_pipeline` as
  a manual upload, and feeds the existing `ingestion-chunking` skill
  unchanged.
