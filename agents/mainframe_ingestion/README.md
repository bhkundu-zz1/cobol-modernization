# Mainframe Ingestion Connector

## Status

Marked **[REAL]** in the scaffolding plan (mock adapter path only). Phase 1
creates folder structure only. Real content lands in **Phase 3**.
`adapter.py` is one of the plan's "critical files."

## Planned scope (architecture.md section 1a; plan's scope decisions)

- `adapter.py` — the common interface (`list_elements(system, subsystem,
  type)`, `get_source(element_id)`, `get_metadata(element_id)`) plus an
  env-driven registry (`SCM_TOOL=endevor|panvalet|changeman|mock`) that the
  MCP gateway's `mainframe_fetch_source` tool selects from.
- `mock_adapter.py` — the only adapter that's actually runnable this pass:
  returns fixture COBOL content, simulating a real element list/pull
  against `fixtures/sample_cobol/PAYROLL01.CBL`.
- `endevor_adapter.py` / `panvalet_adapter.py` / `changeman_adapter.py` —
  real classes implementing the common interface, but their HTTP calls
  raise `NotImplementedError` with a clear message. The seam is real; the
  wire protocol (actual Endevor REST API v2 / ChangeMan ZMF REST API /
  PanValet PAM-or-z/OSMF calls) is future work — see
  `docs/deferred_scope.md`.

This design lets swapping a client's SCM tool be a config change
(`SCM_TOOL` in `.env`) rather than a code change, per architecture.md
section 1a.
