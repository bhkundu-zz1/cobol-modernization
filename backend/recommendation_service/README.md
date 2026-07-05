# Recommendation Service — internal port 8006

## Status

Marked **[REAL]** in the scaffolding plan. Phase 1 creates folder structure
and a placeholder Dockerfile only. Real FastAPI routes land in **Phase 4**.

## Planned scope (architecture.md section 2.2)

- `GET /recommendations` — list/filter `migration_recommendation` docs
  (by `project_id`, `human_review_status`, `confidence_score` range).
- `POST /recommendations/{id}/decision` — records a human
  approve/reject/edit decision, updates `human_review_status`,
  `reviewed_by`, `reviewed_at`, and triggers `audit.append` via MCP.

## Planned layout

```
app/
  main.py
  config.py
  routes/
    recommendations.py
tests/
```
