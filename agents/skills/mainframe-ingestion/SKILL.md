---
name: mainframe-ingestion
description: Triggers a read-only pull of COBOL/JCL/copybook source directly from a client's mainframe SCM tool (Endevor, PanValet, or ChangeMan), producing the same source_upload/source_file shape as a manual upload. Real logic backs the mock adapter path this pass.
model: cobol-analysis-dev
version: 1
inputs:
  - connection parameters (tool, host, credential_ref, system, subsystem, element_type)
  - optional element_id (if omitted, lists elements instead of pulling one)
outputs:
  - source_upload document (source_origin: "mainframe_scm")
  - source_file document(s) (scm_element_ref populated)
tools_allowed:
  - mainframe.fetch_source
  - couchdb.write
  - audit.append
  - kill.check
---

# Mainframe Ingestion Agent

## Purpose

This skill describes how/when to trigger a connector-based pull versus a
manual upload (architecture.md §3.5), and is deliberately editable by a
non-engineer — a client's COBOL SME knows which systems/subsystems actually
matter for a migration engagement, not the harness team. It backs the
second ingestion on-ramp described in architecture.md §1a.

Real this pass, per the plan's scope decision: only the `mock` adapter is
actually runnable (returns fixture COBOL content simulating a real element
list/pull); `EndevorAdapter`/`PanvaletAdapter`/`ChangemanAdapter` are real
classes with the correct interface whose HTTP calls raise
`NotImplementedError` — the seam is real, the wire protocol is future work
(see `docs/deferred_scope.md`).

## When to use a mainframe pull vs. manual upload

Prefer a mainframe pull whenever the client's source of truth for a system
is genuinely the mainframe SCM tool — this is almost always the case for an
active production system, since a manually-exported `.cbl` file risks being
stale relative to what's actually deployed. Manual upload remains
appropriate for: a one-off program a client emails ahead of a formal
connector setup, programs pulled from an already-decommissioned system with
no live SCM access, or a quick demo/PoC before mainframe network access is
provisioned.

## Step 1 — Before you start

- Call `kill.check`. If killed, stop before issuing any mainframe read.
- Confirm `credential_ref` is a reference (e.g. `vault://mainframe/endevor/readonly`),
  never a literal credential value — this skill must never see or log an
  actual password/token, only the reference to where the read-only
  credential is stored (architecture.md §1a).

## Step 2 — List elements (browsing)

When the caller (typically the Upload MFE's element browser, via the
Ingestion BFF's `GET /bff/mainframe-elements`) wants to see what's available
before picking something to pull, call `mainframe.fetch_source` with
`element_id` omitted:

```
mainframe_fetch_source(
  tool="endevor",            # or "panvalet" | "changeman" | "mock"
  host="<from .env or per-call override>",
  credential_ref="vault://mainframe/endevor/readonly",
  system="PAYSYS",
  subsystem="PAYROLL",
  element_type="COBOL",
)
```

This returns `{"elements": [...]}` — a list the UI renders for the user to
pick from. This call is read-only and does not create any `source_upload`/
`source_file` documents by itself.

## Step 3 — Pull one element

Once an element is picked, call `mainframe.fetch_source` again with
`element_id` set:

```
mainframe_fetch_source(
  tool="endevor",
  host="...", credential_ref="...",
  system="PAYSYS", subsystem="PAYROLL", element_type="COBOL",
  element_id="PAYROLL01",
)
```

This returns `{"source_text": "...", "metadata": {...}}`. Using this
result:

1. Create (or reuse, if this is part of a multi-element pull batch) a
   `source_upload` document with `source_origin: "mainframe_scm"` and
   `uploaded_by: "connector:mainframe-<tool>"` (never a human email for a
   connector-driven pull).
2. Create a `source_file` document with the pulled text stored as an
   attachment (same shape as manual upload), `source_origin:
   "mainframe_scm"`, and `scm_element_ref` populated from the returned
   metadata:

```json
{
  "scm_element_ref": {
    "tool": "endevor", "system": "PAYSYS", "subsystem": "PAYROLL",
    "type": "COBOL", "element_id": "PAYROLL01", "version": "12"
  }
}
```

3. Feed the resulting `source_file` into the same `ingestion-chunking`
   skill unchanged — a mainframe-sourced file goes through the identical
   `secret_scan_result` gate as a manually uploaded one (architecture.md
   §1a); mainframe source can carry embedded credentials/PII exactly as an
   upload can.

## Step 4 — Handling a not-yet-implemented tool

If the caller selects a real (non-mock) tool and that adapter's HTTP call
raises `NotImplementedError`, surface this to the caller as a clear,
specific error — "Endevor connector wire protocol not yet implemented; only
the mock adapter is available this pass" — never silently fall back to mock
data and never let the error look like an empty/successful result. This
must fail loud, not quiet.

## Audit requirements

Every `mainframe.fetch_source` call — list or pull — is `audit.append`-logged
(`event_category: "agent_output"`, reusing the existing shape per
architecture.md §1a) with the `credential_ref` used and the element
identifier retrieved, **never the credential itself**.

## Example

Selecting tool `mock`, system `PAYSYS`, subsystem `PAYROLL`, element type
`COBOL`, with `element_id` omitted returns a one-element list containing
`PAYROLL01`; pulling `PAYROLL01` returns the contents of
`fixtures/sample_cobol/PAYROLL01.CBL` as `source_text`, simulating a real
Endevor element pull, and produces a `source_file` with
`source_origin: "mainframe_scm"` and `scm_element_ref.element_id:
"PAYROLL01"`.
