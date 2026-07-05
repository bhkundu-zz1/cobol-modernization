# Q&A / Drilldown Agent — [STUB]

## What will eventually live here

Per architecture.md section 3.6: a lightweight, separate FastAPI endpoint
(outside the main Celery pipeline) plus the `qa-drilldown` skill, letting a
reviewer ask a follow-up question about an already-parsed program (e.g. "why
did you recommend Java here?"). Runs synchronously, still goes through
Guardrails -> LiteLLM, still logged to Langfuse and the audit log. Reads
existing `parsed_structure`/`recommendation` docs via MCP as context; does
not write new recommendation/epic documents (may write an `agent_message`
transcript doc for audit purposes).

## Why this is a stub this pass

`docs/deferred_scope.md` lists the `qa-drilldown` chat endpoint as
explicitly deferred — it's called out in architecture.md itself as
"intentionally thin and secondary, per the product's async-review-queue-first
interaction model." The vertical slice this repo scaffolds focuses on the
core ingest -> analyze -> recommend -> review pipeline; the chat/drilldown
feature is additive UX on top of data the pipeline already produces, so it's
reasonable to defer until the primary path is proven.

The corresponding `agents/skills/qa-drilldown/SKILL.md` is still written in
full this pass (all 7 skills are written now per the plan) — only the
Python endpoint/task code backing it is deferred.

See `docs/deferred_scope.md` for the full reasoning.
