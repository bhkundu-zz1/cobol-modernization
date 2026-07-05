# Upload/Ingestion MFE — port 3001

## Status

Marked **[REAL]** in the scaffolding plan. Phase 1 only creates this
placeholder `package.json`/README plus a Dockerfile. Real components land in
**Phase 5**.

## What will eventually live here (per the plan and architecture.md section 1a/section 8)

- Source-selection tabs: **Manual Upload** | **Connect to mainframe repo**.
- `UploadForm` — manual `.cbl`/`.jcl`/copybook file upload, shows secret-scan
  results, kicks off the pipeline via the Ingestion BFF (`POST /bff/uploads`).
- `MainframeConnectForm.tsx` — tool picker (Endevor/PanValet/ChangeMan), host,
  credential-ref, system/subsystem fields, and an element browser/picker
  backed by `GET /bff/mainframe-elements` (proxying the mock adapter this
  pass — see `agents/mainframe_ingestion/`). Submits via
  `POST /bff/mainframe-pulls`.
- `JobProgress` — polls `GET /bff/jobs/{id}` until the pipeline run completes.

This is one of the plan's "critical files": `src/components/MainframeConnectForm.tsx`.

## Source layout (planned)

```
src/
  components/
    UploadForm.tsx
    MainframeConnectForm.tsx
    JobProgress.tsx
tests/
```
