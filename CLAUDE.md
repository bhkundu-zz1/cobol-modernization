# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

This repository is currently pre-code: it contains only planning/instruction documents (`AGENTS.md`, `.claude/claude.md`). There is no application source, build tooling, or test runner yet. Do not assume a project layout exists — check before referencing paths like `backend/`, `frontend/`, or `skills/`.

## Project goal

This is a harness to help clients plan and execute COBOL/JCL application migrations. It combines LLM agents (open-source and commercial) that read COBOL and JCL source, reason about it, and produce research, recommendations, epics, and stories guiding the migration. Target outcomes:

1. Migrate COBOL programs to microservices in Python or Java Spring Boot, with rationale for the recommended choice per case.
2. Migrate JCL to Python scripts schedulable via Unix shell/cron or Apache Airflow.

## Architecture

- **Frontend**: React, built as independently deployable micro frontends — each runs on its own port as a self-contained app. A failure in one micro frontend must not take down the rest of the application. Use a Python BFF (backend-for-frontend) where a user journey needs page-specific aggregation.
- **API**: Python.
- **Database**: CouchDB.
- **LLM gateway**: LiteLLM (or equivalent) so models can be plugged/switched without touching agent code.
- **Guardrails**: NVIDIA NeMo-based.
- **Agent structure**: agents follow the Anthropic skills/tools folder convention — skills live as markdown files under a `skills/` folder so users can edit agent behavior without code changes. Agents access data/APIs only through an MCP-style gateway.
- **Observability**: Langfuse for agent tracing; all layers need structured logging and exception handling as first-class NFRs.
- **Emergency control**: a kill command must exist to halt any/all agents immediately.

### Non-functional requirements (treat as constraints, not aspirations)

- End-to-end React response time < 5 seconds.
- Error rate < 1%.
- Logging and auditing must satisfy US financial regulatory compliance (SEC and US Treasury requirements for banks/financial services) — this affects retention, traceability, and audit-trail design wherever transactions or recommendations are logged.

## Conventions to follow in every layer

- **Configuration**: use `.env` files for all environment variables; read from `.env` at whatever layer/component needs it. Never hardcode config values — this is a hard requirement to keep code and configuration separate.
- **Testing**: 
  - Python code needs unit tests in the backend's test folder.
  - React code needs unit tests in the frontend's test folder.
  - Run the relevant test suite after writing code, before considering a change done.
- **Micro frontend independence**: each micro frontend is deployable on its own port, independent of the others.
- **Caching**: cache frequently-used/expensive values rather than recomputing or refetching them.

## GitHub

- Repo: https://github.com/bhkundu-zz1/cobol-migration.git
- **Never push/publish to GitHub unless explicitly instructed for that specific action.**
- Before any GitHub publish, update `architecture.md` first so it reflects current state.
