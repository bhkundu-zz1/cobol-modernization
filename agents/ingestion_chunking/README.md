# Ingestion & Chunking Agent

## Status

Marked **[REAL]** in the scaffolding plan. Phase 1 creates folder structure
only. Real content lands in **Phase 3**.

## Planned scope (architecture.md section 3.2, stage [1])

- `task.py` — Celery task entry point. Secret/PII scan (regex + LLM
  classifier) on raw source; splits large files into `chunk` docs
  (paragraph/PROC boundary aware, with overlap); classifies each file
  (`cobol_program | copybook | jcl_job | proc`); writes `source_file`/
  `chunk` docs via MCP.
- `secret_scan.py` — the regex + LLM-classifier secret/PII scan pass.
- `chunker.py` — paragraph/PROC-boundary-aware chunking with overlap.

Backs both ingestion paths (manual upload and mainframe connector pull) —
same `source_file`/`chunk` shape regardless of `source_origin`.
