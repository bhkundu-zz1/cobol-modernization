---
name: migration-recommendation
description: Reasons over a parsed COBOL program or JCL job's structure to recommend a migration target (Python microservice, Java Spring Boot, Python Airflow DAG, or Python cron script), with an explicit rationale, at least one alternative considered, and risk flags.
model: cobol-analysis-dev
version: 1
inputs:
  - cobol_program_structure or jcl_job_structure document
  - copybook fan-in/out data (which other programs share this program's copybooks)
  - client-supplied metadata (team's existing skillset, if provided)
outputs:
  - migration_recommendation document (one per cobol_program_structure or jcl_job_structure)
tools_allowed:
  - couchdb.read
  - couchdb.write
  - audit.append
  - kill.check
---

# Migration Recommendation Agent

## Purpose

This is stage [3] of the pipeline (architecture.md §3.2), and the most
directly client-facing output this pass produces — this is what a reviewer
sees in the Review Queue MFE and decides to approve or reject. The single
most important discipline in this skill is: **never recommend without
showing your work.** A bare "use Python" with no rationale is not an
acceptable output; the guardrail output-schema check (architecture.md §5)
rejects and retries any recommendation missing `rationale`,
`alternative_considered`, or `risk_flags`.

## Before you start

- Call `kill.check`. If killed, stop without writing a recommendation.
- Read the relevant `cobol_program_structure` (or `jcl_job_structure`) via
  `couchdb.read`, plus any other `parsed_structure` documents that share a
  copybook with this program (fan-in/out — programs that share copybooks
  are candidates for being migrated together, or at least reviewed
  together, since splitting them into unrelated services can lose an
  implicit coupling).

## Step 1 — Gather decision factors

Explicitly populate each of these factors before reasoning about a target
— do not let the model jump straight to a conclusion:

- **Complexity**: paragraph count, call graph depth/fan-out, external call
  count (from `cobol_program_structure`), or step count/PROC nesting depth
  (from `jcl_job_structure`).
- **State management**: does the program hold session/transactional state
  across calls, or is it a pure batch transform? (Heavy state management
  favors a stateful service design; pure batch favors a stscript/DAG.)
- **Transaction boundaries**: are there explicit commit/rollback points, or
  external system calls that imply a transaction boundary?
- **Batch vs. online**: is this invoked interactively (implies a
  request/response microservice) or as a scheduled batch step (implies a
  script or DAG task)? JCL job steps are batch by definition; a COBOL
  program's calling context (is it `EXEC PGM=` from a JCL step, or does its
  structure suggest a CICS/online transaction?) is the signal here.
- **Performance sensitivity**: any indication of high-frequency invocation
  or tight latency requirements (comments, naming conventions, external
  call patterns).
- **Integration points**: count of external calls / DD statements / files
  referenced — more integration points generally raises migration risk
  regardless of target.
- **Team's existing skillset** (client-supplied metadata, if present in
  `config_meta`/`client_project` — if absent, do not assume; note its
  absence rather than defaulting silently to one language).
- **Volume/throughput signals** (JCL only): step frequency inferred from
  `schedule_hint_detected`, input file size hints if present.

## Step 2 — Recommendation prompt

**Prompt template:**

```
You are recommending a migration target for a COBOL program (or JCL job)
being modernized off the mainframe. You are given its extracted structure
and a set of decision factors. Recommend exactly one target from this set:
java_spring_boot, python_microservice, python_airflow_dag, python_cron_script.
(COBOL programs are candidates for java_spring_boot or python_microservice;
JCL jobs are candidates for python_airflow_dag or python_cron_script.)

You MUST provide:
1. "rationale": a clear explanation grounded in the decision factors below —
   do not recommend without explaining why, in terms a client's engineering
   lead can evaluate.
2. "alternative_considered": the next-best target and a specific reason it
   was not chosen (not a generic "less suitable").
3. "risk_flags": a list of specific concerns visible in the structure
   (e.g. unresolved external calls, low confidence_score on the input
   structure, heavy state management that any target will need to address
   carefully). An empty list is only acceptable if you state explicitly why
   there are no material risks — do not omit this reasoning.

STRUCTURE:
---
{parsed_structure_json}
---

DECISION FACTORS:
---
{decision_factors_json}
---

Return JSON:
{
  "recommended_target": "...",
  "rationale": "...",
  "confidence_score": <float 0-1>,
  "alternative_considered": {"target": "...", "why_rejected": "..."},
  "risk_flags": ["..."]
}
```

## Step 3 — Confidence scoring

The recommendation's own `confidence_score` should never exceed the input
`cobol_program_structure`/`jcl_job_structure`'s `confidence_score` — a
recommendation can't be more certain than the structural facts it's based
on. If the input structure has `needs_human_review: true`, the
recommendation must carry at least one `risk_flag` calling that out
explicitly (e.g. `"underlying structural extraction flagged for human
review due to N unresolved discrepancies"`).

## Output schema

Write one `migration_recommendation` document (architecture.md §2.2) via
`couchdb.write`:

```json
{
  "type": "migration_recommendation", "project_id": "...",
  "subject_type": "cobol_program|jcl_job", "subject_id": "...",
  "recommended_target": "java_spring_boot|python_microservice|python_airflow_dag|python_cron_script",
  "rationale": "text...", "confidence_score": 0.75,
  "decision_factors": {"complexity": "high", "state_management": "heavy", "batch_vs_online": "online",
                        "performance_sensitivity": "high", "integration_points": 6},
  "alternative_considered": {"target": "python_microservice", "why_rejected": "..."},
  "risk_flags": ["undocumented external CALL to SUBRTN99"],
  "produced_by_agent": "recommendation-agent@v2", "produced_by_model": "<logical model name>",
  "human_review_status": "pending", "reviewed_by": null, "reviewed_at": null
}
```

Immediately follow this write with an `audit.append` call
(`event_category: "agent_output"`) — every recommendation-affecting write is
paired with a real audit event, not optional (project-wide ground rule).

## Guardrail notes

The output rail (architecture.md §5) validates this JSON against the
required-fields schema before it ever reaches CouchDB, retrying with a
corrective re-prompt (bounded retry count) if `rationale`,
`alternative_considered`, or `risk_flags` is missing or empty without
justification. This skill should be written assuming that check exists —
always produce complete output rather than relying on the retry to catch
omissions.

## Example

For `PAYROLL01` (the sample fixture — a simple, self-contained gross-pay
calculator with one unresolved external call to a rate-lookup routine):
`recommended_target: "python_microservice"`, rationale citing low
complexity/no heavy state/no tight latency signal, `alternative_considered:
{"target": "java_spring_boot", "why_rejected": "no evidence of enterprise
integration complexity or existing JVM investment that would justify the
added operational overhead"}`, `risk_flags: ["unresolved external CALL to
rate-lookup routine — target service must confirm data source before
cutover"]`.
