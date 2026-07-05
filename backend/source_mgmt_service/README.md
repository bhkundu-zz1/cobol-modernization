# Source Management Service — internal port 8004

## Status

Marked **[REAL]** in the scaffolding plan. Phase 1 creates folder structure
and a placeholder Dockerfile only. Real FastAPI routes land in **Phase 4**.

## Planned scope (architecture.md sections 1a, 2.2)

- `POST /uploads`, `GET /uploads` — manual file upload lifecycle
  (`source_upload` → `source_file` → `chunk` docs, secret-scan gate).
- `POST /mainframe-pulls` — triggers a connector pull via the MCP gateway's
  `mainframe.fetch_source` tool, producing the same `source_upload`/
  `source_file` shape as manual upload but with `source_origin:
  "mainframe_scm"` and a populated `scm_element_ref`.

## Planned layout

```
app/
  main.py
  config.py
  routes/
    uploads.py
    mainframe_pulls.py
tests/
```
