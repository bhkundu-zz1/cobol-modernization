# Design System

A small shared component library (`Button`, `Table`, `Badge`) published as a
Module Federation shared singleton so every micro frontend renders
consistent UI without duplicating component code or diverging on styling.
Declared as an MF "shared singleton" alongside React itself (see
`frontend/shared-deps`), per architecture.md section 8's shared dependency
governance discussion.

Built out ahead of the plan's original Phase 5 scope (which listed this as
`[STUB]` since the two real MFEs could ship with unstyled markup) because
the component surface needed is small and cheap, and having it real from
the start keeps the Upload and Review Queue MFEs visually consistent
without a later migration.

## Contents

- `src/Button.tsx` — `primary`/`secondary`/`danger` variants
- `src/Table.tsx` — generic typed table with column render functions
- `src/Badge.tsx` — `neutral`/`success`/`warning`/`danger` tone pills
- `src/index.tsx` — barrel export
- `src/__tests__/` — component tests (React Testing Library + Vitest)
