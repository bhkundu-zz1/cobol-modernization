# MCP Gateway — the only path from agent code to CouchDB / external systems

## Status

Marked **[REAL]** in the scaffolding plan. Phase 1 creates folder structure
and a placeholder Dockerfile only. Real content lands in **Phase 2**
(couchdb tools, audit tools, kill tools) and **Phase 3** (mainframe tools).
`app/tools/audit_tools.py` and `app/tools/mainframe_tools.py` are two of the
plan's "critical files."

## Planned scope (architecture.md section 1, section 1a, section 6.2; plan's "Key interfaces")

A single FastMCP-based service exposing:
- `couchdb.read` / `couchdb.write`
- `audit.append` / `audit.export_range` (hash-chained, append-only)
- `kill.check` / `kill.set`
- `mainframe.fetch_source` (real seam, mock adapter runnable this pass)

See `agents/tools/*.md` for the tool declaration docs consumed by skill
authors, and `docs/deferred_scope.md` for what's out of scope this pass.

## Planned layout

```
pyproject.toml
app/
  main.py          # FastMCP server bootstrap
  config.py        # pydantic-settings, reads .env
  couchdb_client.py
  hashing.py
  schemas.py
  tools/
    couchdb_tools.py
    audit_tools.py
    kill_tools.py
    mainframe_tools.py
tests/
  test_couchdb_tools.py
  test_audit_hash_chain.py
  test_kill_tools.py
  test_mainframe_tools.py
```
