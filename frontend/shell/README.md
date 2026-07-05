# Shell (Module Federation host) — port 3000

## Status

Marked **[REAL]** in the scaffolding plan, but Phase 1 only creates this
placeholder `package.json`/README plus a Dockerfile — the actual Vite +
Module Federation host, `RemoteErrorBoundary`, and nav land in **Phase 5**
per the implementation plan.

## What will eventually live here

- Auth/session bootstrap (talks to an Auth BFF for session — not yet
  scaffolded; out of scope for the vertical slice per `docs/deferred_scope.md`
  unless/until auth is prioritized).
- Top nav linking to Upload, Review, Editor, Admin.
- Runtime composition of all 4 remotes via Module Federation 2.0
  (`@module-federation/vite`), each wrapped in its own `RemoteErrorBoundary`
  so one remote failing to load doesn't take down the others
  (architecture.md section 8).
- Remote URLs are read from `.env` (`SHELL_REMOTE_UPLOAD_URL`,
  `SHELL_REMOTE_REVIEW_URL`, `SHELL_REMOTE_EDITOR_URL`,
  `SHELL_REMOTE_ADMIN_URL`) — never hardcoded.

## Source layout (planned)

```
src/
  App.tsx
  RemoteErrorBoundary.tsx
  nav/
  remotes/           # dynamic import() wrappers per remote
tests/
```
