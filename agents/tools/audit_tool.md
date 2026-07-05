# MCP Tool: `audit.append` / `audit.export_range`

Status: **REAL** — backs `mcp_gateway/app/tools/audit_tools.py`. This is the
compliance-critical tool in the system (architecture.md §6.2, CLAUDE.md's
SEC/US Treasury logging requirement) — real hash chaining, not stubbed.

## `audit.append`

```
audit_append(
  project_id: str,
  event_category: "agent_output" | "human_review_decision" |
                  "guardrail_decision" | "export" | "kill_switch" | "config_change",
  actor: {"kind": "agent"|"user"|"system", "id": str},
  action: str,                     # e.g. "created_recommendation"
  subject_doc_id: str,
  subject_doc_rev: str | None,
  before_state_hash: str | None,
  after_state_hash: str | None,
  model_used: str | None,
  skill_version_hash: str | None,
) -> {"id": str, "rev": str, "this_event_hash": str}
```

- Computes `this_event_hash = sha256(canonicalize(event) + prev_event_hash)`,
  where `prev_event_hash` is the latest `audit_event.this_event_hash` for
  this `project_id` (or a fixed genesis constant if none exists yet).
  Altering any past event breaks the chain for every subsequent event —
  this is the tamper-evidence mechanism, verified by walking the chain (see
  `audit.export_range` below).
- **Append-only, structurally**: this tool exposes no update or delete
  method at all — not merely guarded, absent from the interface. A CouchDB
  `validate_doc_update` design-doc function on the `audit_log` database
  additionally rejects any update/delete attempt server-side, so even a
  direct API caller bypassing MCP is blocked by the database itself
  (defense in depth, architecture.md §6.2).
- Call this immediately after every recommendation-affecting write
  (`migration_recommendation`, `epic`, `story`, a human review decision, a
  guardrail rejection/retry, a kill-switch invocation, a config change) —
  every such action must produce exactly one corresponding `audit_event`.

## `audit.export_range`

```
audit_export_range(
  project_id: str,
  start: str,   # ISO8601
  end: str,
) -> {"events": [dict, ...], "chain_valid": bool}
```

- `chain_valid` is computed by walking `prev_event_hash`/`this_event_hash`
  links across the returned events in order; `false` means tampering (or
  data loss) has been detected somewhere in the requested range.
- This is the basic form of the export capability architecture.md §6.2
  describes for producing records "in a reasonably usable electronic
  format" on a client's regulator request. A signed, externally-anchored
  bundle export is deferred (see `docs/deferred_scope.md`) — this pass
  returns the raw ordered event list plus the validity boolean.
