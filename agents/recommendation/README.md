# Migration Recommendation Agent

## Status

Marked **[REAL]** in the scaffolding plan. Phase 1 creates folder structure
only. Real content lands in **Phase 3**.

## Planned scope (architecture.md section 3.2, stage [3])

- `task.py` — reads `parsed_structure` + copybook fan-in/out via MCP;
  reasons per-program: microservice-in-Python vs Java Spring Boot (COBOL) or
  cron-script vs Airflow DAG (JCL); prompts decision factors explicitly
  (statefulness, transaction boundaries, external system calls,
  batch-window/latency sensitivity, team's existing skillset, volume/
  throughput signals); must produce `rationale` + at least one
  `alternative_considered` + explicit `risk_flags` (guardrail-enforced
  output schema); writes `migration_recommendation` via MCP.
- `decision_factors.py` — the structured decision-factor extraction/scoring
  helpers referenced above.
