# COBOL Structural Agent

## Status

Marked **[REAL]** in the scaffolding plan. Phase 1 creates folder structure
only. Real content lands in **Phase 3**. `task.py` is one of the plan's
"critical files."

## Planned scope (architecture.md section 3.2, stage [2a])

- `task.py` — per chunk: extract divisions, paragraphs, call graph, data
  items. Merge-across-chunks pass (stitches call graph, resolves
  cross-chunk references). Self-check pass: re-prompt with the assembled
  structure + original text, ask the model to find
  inconsistencies/omissions. Computes `confidence_score` from self-check
  discrepancy count + chunk count. Writes `cobol_program_structure` via MCP.
- `prompts.py` — prompt templates for extraction + self-check.
- `merge.py` — cross-chunk call-graph stitching / reference resolution.
