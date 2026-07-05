---
name: epic-story-writer
description: Groups migration recommendations into epics by subsystem/copybook-sharing cluster and drafts traceable user stories with acceptance criteria referencing specific COBOL paragraphs or JCL steps.
model: cobol-analysis-dev
version: 1
inputs:
  - migration_recommendation documents (all recommendations for a project_id)
  - cobol_program_structure / jcl_job_structure documents (for call-graph clustering and paragraph/step references)
outputs:
  - epic documents (one per detected cluster)
  - story documents (one or more per epic)
tools_allowed:
  - couchdb.read
  - couchdb.write
  - audit.append
  - kill.check
---

# Epic/Story-Writer Agent

## Status: real, triggered independently of the per-file pipeline

This is stage [4] of the pipeline (architecture.md §3.2), implemented in
`agents/epic_story_writer/task.py`. Unlike stages [1]-[3], it is **not**
appended to `orchestrator/pipeline.py`'s per-file chain — an epic can span
programs from separate uploads/job_runs, so clustering must run across a
project's entire set of recommendations, not one file's. It is triggered
via `POST /jobs/generate-epics-stories` (a manual, project-scoped action —
see the Review Queue's "Generate Epics & Stories" button), consumed by the
dedicated `celery-worker-epic-story` container/queue.

## Purpose (when implemented)

Turn a batch of individually-approved (or pending) migration recommendations
into a client-deliverable backlog: epics grouped by genuine architectural
coupling (not an arbitrary 1-file-1-epic mapping), and stories with
acceptance criteria specific enough that a migration engineer can implement
against them without re-reading the original COBOL.

## Before you start

- Call `kill.check`. If killed, stop without writing epic/story documents.
- Read all `migration_recommendation` documents for the `project_id`, plus
  their corresponding `cobol_program_structure`/`jcl_job_structure`
  documents' `call_graph` / `copybooks_referenced` fields.

## Step 0 — Understand each program

Before any grouping or drafting happens, every program gets read and
explained in plain English by a separate agent/skill,
`agents/skills/cobol-code-understanding/SKILL.md` — a human-readable,
max-600-word summary of what the program does, grounded in its raw source
and structure. This mirrors how a human team actually works: an engineer
reads and explains the code before a product manager breaks it into a
backlog. The summary is persisted as `plain_english_summary` on the
program's `cobol_program_structure` document and reused across
epic/story-generation runs — a program already understood is not
re-summarized. See that skill file for the prompt and word-count
guardrail; this skill only consumes its output.

## Step 1 — Cluster into epics

Do **not** default to one epic per program. Build a graph where programs
are connected if they share a copybook (`copybooks_referenced` overlap) or
have a resolved external `CALL` between them (`call_graph.edges`). Compute
connected components. Each connected component with 2+ programs becomes one
epic candidate; a program with no shared copybooks or calls to/from any
other analyzed program becomes its own single-program epic — that is a
legitimate outcome, not a fallback failure.

**Clustering guidance prompt (used to name/describe each cluster, not to
compute the graph itself — the graph is computed deterministically, not by
the model). Reads each program's Step 0 plain-English summary, not raw
structure JSON — the epic is written from the human-readable understanding
of what these programs do, not from paragraph/call-graph metadata:**

```
You are naming a migration epic. Here is a cluster of COBOL programs that
share copybooks or call each other, along with their individual migration
recommendations. Write a short epic title (subsystem-oriented, e.g. "Payroll
gross-pay calculation subsystem", max 50 words) and a 2-4 sentence
description of what this cluster does collectively and why it's being
migrated together.

CLUSTER PROGRAMS AND RECOMMENDATIONS:
---
{cluster_summary_json}
---

Return JSON: {"title": "...", "description": "..."}
```

The title is guardrail-checked at 50 words or fewer — it stays short and
subsystem-oriented by design; the description has no word cap.

## Step 2 — Draft stories per epic

For each program in the epic, draft one or more stories. A story's
`acceptance_criteria` must reference specific paragraph names (COBOL) or
step names (JCL) from the underlying structure — generic criteria like
"migrate the business logic correctly" are not acceptable; criteria should
name the paragraphs/steps a reviewer can go check against the original
source. The model is given **both** the Step 0 plain-English summary
(narrative context — what the program is for) **and** the structured
paragraph/call-graph data (for citation) — the summary alone is not
sufficient grounding for specific acceptance criteria.

**Story-drafting prompt template:**

```
You are drafting a user story for a COBOL-to-{recommended_target} migration
task, part of the epic "{epic_title}". Write acceptance criteria that
reference specific paragraph names or JCL step names from the structure
below, not generic statements.

PROGRAM UNDERSTANDING:
---
{plain_english_summary}
---

PROGRAM STRUCTURE:
---
{cobol_program_structure_json}
---

RECOMMENDATION:
---
{migration_recommendation_json}
---

Return JSON:
{
  "title": "...",
  "description": "...",
  "acceptance_criteria": ["References paragraph 2000-CALC-GROSS: ...", ...]
}
```

## Output schema

```json
{
  "type": "epic", "project_id": "...", "title": "...", "description": "..."
}
```

```json
{
  "type": "story", "project_id": "...", "epic_id": "epic-uuid",
  "title": "Extract payroll gross-pay calculation into Python microservice",
  "description": "...", "acceptance_criteria": ["..."],
  "source_program_ids": ["PAYROLL01"],
  "generated_by_agent": "epic-story-writer@v1", "edited_by_human": false,
  "edit_history_ref": null,
  "export_status": "not_exported", "jira_issue_key": null
}
```

## Guardrail notes

Every `acceptance_criteria` entry should be checkable against the
underlying `cobol_program_structure`/`jcl_job_structure` — if a criterion
can't be traced to a specific paragraph/step in the structure, it's likely
the model inferring behavior not actually extracted, which repeats the same
untrusted-inference risk this whole system is designed to guard against
(architecture.md §3.4). The epic title's 50-word cap is enforced the same
way Step 0's 600-word summary cap is — a schema-validation constraint that
rejects and retries an over-length response, not a truncation.

## Example (illustrative — not exercised by any runnable code this pass)

`PAYROLL01` (no shared copybooks with any other analyzed program in the
sample fixture set) would become its own single-program epic, "Payroll
gross-pay calculation," with one story whose acceptance criteria reference
`1000-MAIN` and `2000-CALC-GROSS` by name.
