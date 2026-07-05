# Agent tests

## Status

Folder created in Phase 1; real tests land alongside their corresponding
agent code in Phase 3.

## Planned coverage (per the plan's directory tree)

- `chunker` — chunk boundary/overlap correctness
- `secret_scan` — regex + classifier detection cases
- `cobol_structural` task — extraction + self-check + confidence scoring
- `merge` — cross-chunk call-graph stitching
- `recommendation` task — decision-factor reasoning, schema compliance
- `confidence` — shared confidence-score computation
- `guardrails_client` — local Pydantic schema validation stub
- mainframe adapter registry + mock adapter — `list_elements`/`get_source`
  against the mock adapter; confirm `EndevorAdapter`/`PanvaletAdapter`/
  `ChangemanAdapter` raise `NotImplementedError` cleanly
