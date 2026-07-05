from app.schemas import CouchDBReadRequest, CouchDBWriteRequest
from app.tools.couchdb_tools import AuditLogWriteRejected, couchdb_read, couchdb_write


def test_write_then_read_roundtrip(fake_couchdb):
    write_result = couchdb_write(
        fake_couchdb,
        CouchDBWriteRequest(
            database="sources",
            doc={"type": "source_file", "source_file_id": "sf-1", "filename": "PAYROLL01.CBL"},
            project_id="acme-2026",
            created_by="user:test@example.com",
            trace_id="trace-1",
        ),
    )
    assert write_result.id
    assert write_result.rev

    read_result = couchdb_read(fake_couchdb, CouchDBReadRequest(database="sources", doc_id=write_result.id))
    assert len(read_result.docs) == 1
    assert read_result.docs[0]["filename"] == "PAYROLL01.CBL"
    assert read_result.docs[0]["project_id"] == "acme-2026"


def test_write_is_idempotent_for_singular_docs(fake_couchdb):
    request = CouchDBWriteRequest(
        database="parsed_structure",
        doc={
            "type": "cobol_program_structure",
            "source_file_id": "sf-1",
            "program_id": "PAYROLL01",
            "confidence_score": 0.5,
        },
        project_id="acme-2026",
        created_by="agent:cobol-structural@v1",
        trace_id="trace-1",
    )

    first = couchdb_write(fake_couchdb, request)
    second = couchdb_write(fake_couchdb, request)

    assert first.id == second.id, "retried write for the same logical doc should overwrite, not duplicate"

    found = fake_couchdb.find("parsed_structure", {"source_file_id": "sf-1", "type": "cobol_program_structure"})
    assert len(found["docs"]) == 1


def test_mango_selector_read(fake_couchdb):
    for i in range(3):
        couchdb_write(
            fake_couchdb,
            CouchDBWriteRequest(
                database="recommendations",
                doc={"type": "migration_recommendation", "human_review_status": "pending", "seq": i},
                project_id="acme-2026",
                created_by="agent:recommendation@v1",
                trace_id="trace-1",
            ),
        )

    result = couchdb_read(
        fake_couchdb,
        CouchDBReadRequest(
            database="recommendations",
            mango_selector={"project_id": "acme-2026", "human_review_status": "pending"},
        ),
    )
    assert len(result.docs) == 3


def test_couchdb_write_rejects_audit_log_database(fake_couchdb):
    try:
        couchdb_write(
            fake_couchdb,
            CouchDBWriteRequest(
                database="audit_log",
                doc={"type": "audit_event"},
                project_id="acme-2026",
                created_by="user:test@example.com",
                trace_id="trace-1",
            ),
        )
        assert False, "expected AuditLogWriteRejected"
    except AuditLogWriteRejected:
        pass
