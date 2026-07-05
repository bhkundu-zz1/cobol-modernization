# Review BFF — port 8002

## Status

Marked **[REAL]** in the scaffolding plan. Phase 1 creates folder structure
and a placeholder Dockerfile only. Real FastAPI routes land in **Phase 4**.
`app/routes/review_items.py` is one of the plan's "critical files."

## Planned scope (architecture.md sections 8, 9.1; plan's "Key interfaces")

- `GET /bff/review-items` — fans out recommendation + structure summary +
  job progress concurrently, Redis TTL-cached (`REDIS_DB_CACHE`, see
  `.env.example`), invalidated on decision writes rather than relying on
  blind TTL alone where possible.
- `POST /bff/review-items/{id}/decision` — proxies to the recommendation
  service, triggers `audit.append`, invalidates the cache entry.

## Planned layout

```
app/
  main.py
  config.py
  cache.py
  routes/
    review_items.py
tests/
```
