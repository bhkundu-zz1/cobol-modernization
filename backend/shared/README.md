# Backend Shared — Pydantic models + MCP client

## Status

Marked **[REAL]** in the scaffolding plan. Phase 1 creates folder structure
only. Real content lands in **Phase 2** (`models/`) and is referenced by
`agents/common/mcp_client.py`'s canonical implementation, which per the
plan lives at `backend/shared/mcp_client.py` and is imported by both
`agents/` and the FastAPI services as a local path dependency (DRY within
this monorepo — no independent-packaging pressure yet).

## Planned scope (architecture.md section 2.2, plan's "Key interfaces")

`models/` — one Pydantic model per CouchDB document shape:
- `DocEnvelope` mixin (id/rev/type/schema_version/project_id/created_at/
  created_by/updated_at/trace_id)
- `SourceUpload`, `SourceFile`, `Chunk`
- `CobolProgramStructure`, `JclJobStructure` (stub-shape),
  `CopybookStructure` (stub-shape)
- `MigrationRecommendation`, `RiskAssessment` (stub-shape)
- `Epic` / `Story` (stub-shape)
- `JobRun` / `AgentTask`
- `AuditEvent`

Field lists per architecture.md sections 2.2/6.2 exactly.

## Planned layout

```
models/
  __init__.py
  envelope.py
  source.py
  parsed_structure.py
  recommendation.py
  backlog.py
  job_run.py
  audit.py
mcp_client.py
tests/
  test_model_validation.py
```
