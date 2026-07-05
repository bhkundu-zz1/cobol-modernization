# Review Queue / Dashboard MFE — port 3002

## Status

Marked **[REAL]** in the scaffolding plan. Phase 1 only creates this
placeholder `package.json`/README plus a Dockerfile. Real components land in
**Phase 5**.

## What will eventually live here (per architecture.md section 8, section 3.4)

- `ReviewQueueTable` — sortable/filterable list of parsed programs and their
  `migration_recommendation`s, surfacing `confidence_score` and
  `needs_human_review` so low-confidence items are triaged first (never
  silently presented as ground truth — architecture.md section 3.4).
- `ApproveRejectControls` — approve/reject/comment actions that call
  `POST /bff/review-items/{id}/decision` on the Review BFF, which proxies to
  the recommendation service and triggers `audit.append`.
- Data comes from `GET /bff/review-items` (fanned-out + Redis TTL-cached on
  the BFF side).

## Source layout (planned)

```
src/
  components/
    ReviewQueueTable.tsx
    ApproveRejectControls.tsx
tests/
```
