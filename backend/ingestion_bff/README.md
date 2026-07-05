# Ingestion BFF — port 8001

## Status

Marked **[REAL]** in the scaffolding plan. Phase 1 creates folder structure
and a placeholder Dockerfile only. Real FastAPI routes land in **Phase 4**.

## Planned scope (architecture.md sections 1a, 8, 9.1; plan's "Key interfaces")

- `POST /bff/uploads` — 202 + `job_run_id`, fans out to source-mgmt-service
  and job-pipeline-control-service concurrently (`asyncio.gather`).
- `POST /bff/mainframe-pulls` — same 202 + `job_run_id` shape, body
  `{tool, host, credential_ref, system, subsystem, element_id}`, fans out to
  source-mgmt's `/mainframe-pulls` + job-pipeline-control.
- `GET /bff/mainframe-elements` — proxies `mainframe.fetch_source` list mode
  for the Upload MFE's element browser.
- `GET /bff/jobs/{id}` — proxies job-pipeline-control's job status.

## Planned layout

```
app/
  main.py
  config.py
  routes/
    uploads.py
    mainframe_pulls.py
    jobs.py
tests/
```
