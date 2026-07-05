# MCP Tool: `couchdb.read` / `couchdb.write`

Status: **REAL** — backs `mcp_gateway/app/tools/couchdb_tools.py`.

These are the only tools any agent uses to read or write CouchDB data.
Agents never hold a CouchDB driver or connection string directly
(architecture.md §1 "Connection rules") — the MCP gateway is the sole
mediator, so every read/write is uniformly auditable and access-controlled
at one chokepoint.

## `couchdb.read`

```
couchdb_read(
  database: str,                      # one of: sources, parsed_structure,
                                       # agent_runs, recommendations, backlog,
                                       # audit_log, config_meta
  doc_id: str | None = None,          # direct GET by id
  mango_selector: dict | None = None, # POST /db/_find body, used when doc_id is None
  limit: int = 50,
) -> {"docs": [dict, ...], "bookmark": str | None}
```

- Exactly one of `doc_id` or `mango_selector` should be provided.
- `mango_selector` queries should target one of the indexes documented in
  architecture.md §2.3 (e.g. `{"project_id": ..., "type": ...,
  "human_review_status": ...}`) — ad hoc unindexed selectors are allowed but
  slow at scale; prefer the documented index shapes.

## `couchdb.write`

```
couchdb_write(
  database: str,
  doc: dict,          # must include "type"; envelope fields (schema_version,
                       # created_at, updated_at, trace_id) are populated/
                       # validated by the gateway, not the caller
  project_id: str,
  created_by: str,     # "agent:<name>@v<version>" | "user:<email>" | "connector:<name>"
  trace_id: str,
) -> {"id": str, "rev": str}
```

- **Idempotency**: callers supply (or the gateway derives) a deterministic
  `_id` for documents that are logically singular per
  `(project_id, source_file_id, type)` — e.g. one `cobol_program_structure`
  per source file — so a retried Celery task overwrites the same logical
  document instead of creating a duplicate (architecture.md §9.2).
- This tool does **not** write to the `audit_log` database — use
  `audit.append` for that (see `audit_tool.md`); `couchdb.write` rejects
  `database="audit_log"` at the gateway layer.
