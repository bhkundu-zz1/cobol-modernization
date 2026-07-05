"""Create the 7 CouchDB databases + Mango indexes (architecture.md section 2.3).

Idempotent: safe to re-run against an already-initialized CouchDB instance.
Reads all connection settings from mcp_gateway's config (which itself reads
.env) — no hardcoded values.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from mcp_gateway.app.config import settings  # noqa: E402
from mcp_gateway.app.couchdb_client import get_couchdb_client  # noqa: E402

# architecture.md section 2.3 specifies the "idx_recency" index as
# {project_id asc, type asc, created_at desc} — but CouchDB Mango indexes
# reject mixed sort directions within one index ("unsupported_mixed_sort"),
# confirmed against a live CouchDB 3.3 instance. All fields are ascending
# here; callers wanting newest-first order reverse the result client-side
# (small result sets per query — review-queue/recency lists — so this is
# cheap) rather than needing a second, descending-only index.
MANGO_INDEXES: dict[str, list[tuple[dict, str]]] = {
    settings.couchdb_db_recommendations: [
        (
            {"fields": [{"project_id": "asc"}, {"type": "asc"}, {"human_review_status": "asc"}]},
            "idx_review_queue",
        ),
        (
            {"fields": [{"project_id": "asc"}, {"type": "asc"}, {"created_at": "asc"}]},
            "idx_recency",
        ),
        ({"fields": [{"source_file_id": "asc"}]}, "idx_source_file_lookup"),
    ],
    settings.couchdb_db_parsed_structure: [
        (
            {"fields": [{"project_id": "asc"}, {"type": "asc"}, {"created_at": "asc"}]},
            "idx_recency",
        ),
        ({"fields": [{"source_file_id": "asc"}]}, "idx_source_file_lookup"),
    ],
    settings.couchdb_db_agent_runs: [
        ({"fields": [{"job_run_id": "asc"}, {"started_at": "asc"}]}, "idx_pipeline_timeline"),
        (
            {"fields": [{"project_id": "asc"}, {"type": "asc"}, {"created_at": "asc"}]},
            "idx_recency",
        ),
    ],
    settings.couchdb_db_sources: [
        (
            {"fields": [{"project_id": "asc"}, {"type": "asc"}, {"created_at": "asc"}]},
            "idx_recency",
        ),
    ],
    settings.couchdb_db_backlog: [
        (
            {"fields": [{"project_id": "asc"}, {"type": "asc"}, {"created_at": "asc"}]},
            "idx_recency",
        ),
    ],
}

AUDIT_LOG_VALIDATE_DOC_UPDATE = """
function(newDoc, oldDoc, userCtx) {
  if (oldDoc && !newDoc._deleted) {
    throw({forbidden: "audit_log documents are append-only: updates are not permitted."});
  }
  if (newDoc._deleted) {
    throw({forbidden: "audit_log documents are append-only: deletes are not permitted."});
  }
}
""".strip()


def main() -> int:
    client = get_couchdb_client()

    for db_name in settings.known_databases():
        client.ensure_database(db_name)
        print(f"ensured database: {db_name}")

    for db_name, indexes in MANGO_INDEXES.items():
        for index_def, index_name in indexes:
            try:
                client.create_index(db_name, index_def, index_name)
                print(f"ensured index {index_name} on {db_name}")
            except Exception as exc:  # noqa: BLE001 - index-already-exists is not fatal
                print(f"index {index_name} on {db_name}: {exc}", file=sys.stderr)

    client.put_design_document(
        settings.couchdb_db_audit_log,
        "_design/validate",
        {"validate_doc_update": AUDIT_LOG_VALIDATE_DOC_UPDATE},
    )
    print(f"installed validate_doc_update design doc on {settings.couchdb_db_audit_log}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
