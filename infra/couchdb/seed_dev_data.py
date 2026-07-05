"""Seed development data — [STUB]

## What this will eventually do

Populate a local CouchDB instance with representative sample documents
(a `client_project` config_meta doc, maybe a pre-parsed `cobol_program_structure`
and `migration_recommendation` for demo purposes) so a developer can explore
the Review Queue UI without first running the full pipeline against
`fixtures/sample_cobol/PAYROLL01.CBL`.

## Why this is a stub this pass

Not needed for the Phase 1-3 verification path, which exercises the real
pipeline end-to-end against the sample fixture instead of relying on
pre-seeded fake data (the plan explicitly favors "real, working end-to-end
path" over "fake/simulated logic" wherever a real path is in scope this
pass). Seeding synthetic data is a convenience for later UI/demo work, not a
dependency of any phase's verification step — see docs/deferred_scope.md.

This module is intentionally a documented no-op: it is safe to import and
call, does nothing, and says so, so it can be wired into `make` targets or
CI later without erroring.
"""


def seed() -> None:
    """No-op. See module docstring for planned scope and why this is deferred."""
    print(
        "infra/couchdb/seed_dev_data.py: no-op stub (Phase 1). "
        "See docs/deferred_scope.md."
    )


if __name__ == "__main__":
    seed()
