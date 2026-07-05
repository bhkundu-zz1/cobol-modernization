"""Seeds manually-authored epic/story fixtures into CouchDB, so the Editor
MFE can be built and tested without wiring the epic-story-writer agent into
the Celery pipeline chain (docs/deferred_scope.md).

Idempotent: uses deterministic _ids derived from title, safe to re-run.
Reads connection settings from mcp_gateway's config (same as
infra/couchdb/init_databases.py), since this is a dev/ops utility script,
not agent code subject to the "agents never touch CouchDB directly" rule.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from mcp_gateway.app.config import settings  # noqa: E402
from mcp_gateway.app.couchdb_client import get_couchdb_client  # noqa: E402

PROJECT_ID = "acme-2026"

EPICS = [
    {
        "_id": f"{PROJECT_ID}:epic:payroll-gross-pay",
        "title": "Extract payroll gross-pay calculation",
        "description": "Migrate PAYROLL01's gross-pay calculation subsystem off the mainframe.",
    },
    {
        "_id": f"{PROJECT_ID}:epic:payroll-overtime-rules",
        "title": "Modernize overtime calculation rules",
        "description": "Extract and modernize overtime-rate business rules embedded in PAYROLL01.",
    },
]

STORIES = [
    {
        "_id": f"{PROJECT_ID}:story:extract-gross-pay-service",
        "epic_id": EPICS[0]["_id"],
        "title": "Extract gross-pay calculation into Python microservice",
        "description": "Move 2000-CALC-GROSS's gross-pay computation into a standalone Python microservice.",
        "acceptance_criteria": [
            "Service returns the same gross-pay result as PAYROLL01 for all known test cases",
            "Overtime hours (>40) are correctly split at 1.5x rate",
        ],
        "source_program_ids": ["PAYROLL01:1000-MAIN", "PAYROLL01:2000-CALC-GROSS"],
        "generated_by_agent": "epic-story-writer@v1",
    },
    {
        "_id": f"{PROJECT_ID}:story:resolve-rate-lookup-dependency",
        "epic_id": EPICS[0]["_id"],
        "title": "Resolve external rate-lookup dependency (SUBRTN99)",
        "description": "PAYROLL01 calls an external, unresolved subroutine SUBRTN99 to look up hourly rates. Identify and migrate this dependency before cutover.",
        "acceptance_criteria": [
            "SUBRTN99's actual data source is identified and documented",
            "The new service has an equivalent, testable rate-lookup mechanism",
        ],
        "source_program_ids": ["PAYROLL01:2000-CALC-GROSS"],
        "generated_by_agent": "epic-story-writer@v1",
    },
    {
        "_id": f"{PROJECT_ID}:story:overtime-threshold-config",
        "epic_id": EPICS[1]["_id"],
        "title": "Make the 40-hour overtime threshold configurable",
        "description": "PAYROLL01 hardcodes the 40-hour weekly overtime threshold. The modernized service should read this from configuration.",
        "acceptance_criteria": ["Threshold is read from an environment variable or config service, not hardcoded"],
        "source_program_ids": ["PAYROLL01:2000-CALC-GROSS"],
        "generated_by_agent": "epic-story-writer@v1",
    },
]


def main() -> int:
    client = get_couchdb_client()

    for epic in EPICS:
        doc = dict(epic)
        doc["type"] = "epic"
        doc["project_id"] = PROJECT_ID
        doc["created_by"] = "system:seed_epics_stories"
        existing = client.get_document(settings.couchdb_db_backlog, doc["_id"])
        if existing is not None:
            doc["_rev"] = existing["_rev"]
        client.put_document(settings.couchdb_db_backlog, doc)
        print(f"seeded epic: {doc['title']}")

    for story in STORIES:
        doc = dict(story)
        doc["type"] = "story"
        doc["project_id"] = PROJECT_ID
        doc["created_by"] = "system:seed_epics_stories"
        doc.setdefault("export_status", "not_exported")
        doc.setdefault("edited_by_human", False)
        doc.setdefault("edit_history_ref", [])
        existing = client.get_document(settings.couchdb_db_backlog, doc["_id"])
        if existing is not None:
            doc["_rev"] = existing["_rev"]
        client.put_document(settings.couchdb_db_backlog, doc)
        print(f"seeded story: {doc['title']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
