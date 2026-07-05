# AGENTS.md

## Purpose
This file guides AI coding agents on how to work productively in the `cobol-modernization` repository.

## Current Repository State
- The workspace currently contains only `.claude/claude.md` and no application source code.
- Use this file as the primary instruction source until a fuller project structure exists.

## Key Project Conventions
- Always use `.env` files for configuration. Avoid hardcoding values in code.
- Environment variables must be read from `.env` at every application layer or component.
- Update `architecture.md` before publishing to GitHub.
- Do not publish anything to GitHub unless explicitly instructed.

## Architecture Expectations
Agents should assume the project is a COBOL migration harness with:
- UI in React
- API layer in Python
- Database as CouchDB
- Microservice-based architecture with individually deployable micro frontends
- BFF or Python backend support if required for user journeys
- Cache frequently used values where appropriate
- If one micro frontend fails, the whole application must continue operating
- Agent gateway support for switchable LLMs (LiteLLM-style)
- Guardrails informed by NVIDIA NeMo
- Observability via Langfuse-style logging and tracing
- Kill command support for emergency agent termination

## Functional and Non-Functional Requirements
- Support reading and reasoning on COBOL and JCL code
- Generate migration recommendations, epics, and stories
- Target end-to-end React response time < 5 seconds
- Keep error rate < 1%
- Implement logging and auditing for SEC / US Treasury financial compliance

## Agent and Skill Conventions
- Agents should use skills stored in markdown files under a `skills/` folder when present.
- Agents should access data and APIs via an MCP-style gateway.
- Agent behavior should be observable and logged.
- Include a kill command for emergency shutdown of agents.

## Testing Conventions
- Create Python unit tests in the backend test folder once backend code exists.
- Create React unit tests in the frontend test folder once frontend code exists.
- Unit tests are a best practice and should be run after code changes.

## Future Guidance
- When source directories appear, create separate instructions for frontend, backend, and agent tooling.
- Preserve existing documentation and link to it rather than duplicating it.
- If `architecture.md` or `README.md` are added later, update this file to reference them.
