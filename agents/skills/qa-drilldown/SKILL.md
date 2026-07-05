---
name: qa-drilldown
description: Answers a reviewer's follow-up question about one already-parsed program or job ("why did you recommend Java here?"), reading existing parsed_structure/recommendation documents as context. Does not write new recommendation/epic documents.
model: cobol-analysis-dev
version: 1
inputs:
  - a reviewer's free-text question
  - subject_id (the cobol_program_structure/jcl_job_structure/migration_recommendation being asked about)
outputs:
  - an answer returned synchronously to the caller
  - an agent_message transcript document (for audit purposes)
tools_allowed:
  - couchdb.read
  - couchdb.write
  - audit.append
  - kill.check
---

# Q&A / Drilldown Agent

## Purpose

This is the secondary, non-pipeline feature described in architecture.md
§3.6: a reviewer looking at one recommendation in the Review Queue MFE can
ask a follow-up question ("why did you recommend Java here?", "what would
change if this program had no external calls?") without re-running the
whole pipeline. It is explicitly **not implemented as a running endpoint
this pass** — no FastAPI route exists yet (see `docs/deferred_scope.md`) —
but this skill is written now so the behavior contract is settled before
that endpoint is built.

Kept intentionally thin and secondary, per the product's async-review-queue-
first interaction model: this is a convenience on top of already-produced
output, not a new source of recommendations.

## Before you start

- Call `kill.check`. If killed, decline to answer and say so plainly.
- Read the relevant `cobol_program_structure`/`jcl_job_structure` and
  `migration_recommendation` document(s) via `couchdb.read` — this is the
  only context the answer should be grounded in.

## Answering

**Prompt template:**

```
A reviewer is asking a follow-up question about a COBOL/JCL migration
recommendation. Answer using ONLY the structure and recommendation data
below — if the answer requires information not present in either, say so
explicitly rather than speculating.

STRUCTURE:
---
{parsed_structure_json}
---

RECOMMENDATION:
---
{migration_recommendation_json}
---

REVIEWER QUESTION:
---
{question}
---

Answer directly and concisely, citing specific fields (paragraph names,
risk_flags, decision_factors) where relevant.
```

This runs synchronously (not through Celery), still goes through
`guardrails_client.check_input`/`check_output` → LiteLLM, and is still
logged to Langfuse and the audit log like every other LLM call in this
system.

## What this skill must never do

- Never write a new `migration_recommendation`, `cobol_program_structure`,
  `epic`, or `story` document — this is a read-and-explain skill, not a
  re-analysis skill. If the reviewer's question implies the original
  recommendation might be wrong, say so in the answer and suggest a human
  re-review, but do not silently produce a competing recommendation
  document.
- Never answer from anything other than the specific subject's own
  documents — no cross-project or cross-program context leakage.

## Output

Return the answer text synchronously to the caller. Additionally write one
`agent_message` document (architecture.md §2.1, `agent_runs` database) as a
transcript record for audit purposes:

```json
{
  "type": "agent_message", "project_id": "...", "job_run_id": null,
  "subject_id": "...", "question": "...", "answer": "...",
  "asked_by": "user:<email>"
}
```

## Example

Reviewer asks, for `PAYROLL01`: "why not Java Spring Boot?" — the answer
should cite the recommendation's own `alternative_considered.why_rejected`
field directly rather than re-deriving a new justification, since the
original reasoning is already recorded and should be quoted, not
reinvented.
