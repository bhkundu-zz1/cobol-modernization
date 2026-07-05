from agents.common.guardrails_client import GuardrailRejection
from agents.recommendation.task import run_migration_recommendation

STRUCTURE = {
    "_id": "acme-2026:sf-1:cobol_program_structure",
    "source_file_id": "sf-1",
    "program_id": "PAYROLL01",
    "paragraphs": [{"name": "1000-MAIN", "calls": [], "performs": ["2000-CALC-GROSS"]}],
    "call_graph": {"nodes": ["1000-MAIN", "2000-CALC-GROSS"], "edges": [{"from": "1000-MAIN", "to": "2000-CALC-GROSS"}]},
    "external_calls": [{"target": "SUBRTN99", "call_type": "CALL", "resolved": False}],
    "confidence_score": 0.85,
    "needs_human_review": False,
}

VALID_RECOMMENDATION = {
    "recommended_target": "python_microservice",
    "rationale": "low complexity, no heavy state, no tight latency signal",
    "confidence_score": 0.95,
    "alternative_considered": {"target": "java_spring_boot", "why_rejected": "no JVM investment justifying overhead"},
    "risk_flags": ["unresolved external CALL to rate-lookup routine"],
}


def test_recommendation_written_with_required_fields(fake_mcp_client, make_fake_llm_client):
    llm = make_fake_llm_client([VALID_RECOMMENDATION])

    result = run_migration_recommendation(
        project_id="acme-2026",
        job_run_id="jr-1",
        agent_task_id="task-1",
        cobol_program_structure=STRUCTURE,
        mcp_client=fake_mcp_client,
        llm_client=llm,
    )

    doc = fake_mcp_client.databases["recommendations"][result["migration_recommendation_id"]]
    assert doc["rationale"]
    assert doc["alternative_considered"]
    assert doc["risk_flags"]
    assert doc["human_review_status"] == "pending"


def test_recommendation_confidence_capped_by_structure_confidence(fake_mcp_client, make_fake_llm_client):
    llm = make_fake_llm_client([VALID_RECOMMENDATION])  # LLM claims 0.95, structure is 0.85

    result = run_migration_recommendation(
        project_id="acme-2026",
        job_run_id="jr-1",
        agent_task_id="task-1",
        cobol_program_structure=STRUCTURE,
        mcp_client=fake_mcp_client,
        llm_client=llm,
    )
    doc = fake_mcp_client.databases["recommendations"][result["migration_recommendation_id"]]
    assert doc["confidence_score"] == 0.85


def test_needs_human_review_structure_adds_risk_flag(fake_mcp_client, make_fake_llm_client):
    structure = {**STRUCTURE, "needs_human_review": True}
    llm = make_fake_llm_client([VALID_RECOMMENDATION])

    result = run_migration_recommendation(
        project_id="acme-2026",
        job_run_id="jr-1",
        agent_task_id="task-1",
        cobol_program_structure=structure,
        mcp_client=fake_mcp_client,
        llm_client=llm,
    )
    doc = fake_mcp_client.databases["recommendations"][result["migration_recommendation_id"]]
    assert any("flagged for human review" in flag for flag in doc["risk_flags"])


def test_missing_required_field_rejected_after_retry_exhausted(fake_mcp_client, make_fake_llm_client):
    incomplete = {"recommended_target": "python_microservice", "rationale": "x", "confidence_score": 0.5}
    llm = make_fake_llm_client([incomplete, incomplete])  # first call + one retry, both bad

    try:
        run_migration_recommendation(
            project_id="acme-2026",
            job_run_id="jr-1",
            agent_task_id="task-1",
            cobol_program_structure=STRUCTURE,
            mcp_client=fake_mcp_client,
            llm_client=llm,
        )
        assert False, "expected GuardrailRejection"
    except GuardrailRejection:
        pass

    assert fake_mcp_client.databases.get("recommendations", {}) == {}


def test_subject_filename_denormalized_from_source_file(fake_mcp_client, make_fake_llm_client):
    fake_mcp_client.couchdb_write(
        database="sources",
        doc={"_id": "acme-2026:sf-1:source_file", "type": "source_file", "filename": "PAYROLL01.CBL"},
        project_id="acme-2026",
        created_by="agent:ingestion-chunking@v1",
        trace_id="jr-1",
    )
    llm = make_fake_llm_client([VALID_RECOMMENDATION])

    result = run_migration_recommendation(
        project_id="acme-2026",
        job_run_id="jr-1",
        agent_task_id="task-1",
        cobol_program_structure=STRUCTURE,
        mcp_client=fake_mcp_client,
        llm_client=llm,
    )
    doc = fake_mcp_client.databases["recommendations"][result["migration_recommendation_id"]]
    assert doc["subject_filename"] == "PAYROLL01.CBL"


def test_subject_filename_is_none_when_source_file_missing(fake_mcp_client, make_fake_llm_client):
    llm = make_fake_llm_client([VALID_RECOMMENDATION])

    result = run_migration_recommendation(
        project_id="acme-2026",
        job_run_id="jr-1",
        agent_task_id="task-1",
        cobol_program_structure=STRUCTURE,
        mcp_client=fake_mcp_client,
        llm_client=llm,
    )
    doc = fake_mcp_client.databases["recommendations"][result["migration_recommendation_id"]]
    assert doc["subject_filename"] is None


def test_program_id_set_from_structure(fake_mcp_client, make_fake_llm_client):
    llm = make_fake_llm_client([VALID_RECOMMENDATION])

    result = run_migration_recommendation(
        project_id="acme-2026",
        job_run_id="jr-1",
        agent_task_id="task-1",
        cobol_program_structure=STRUCTURE,
        mcp_client=fake_mcp_client,
        llm_client=llm,
    )
    doc = fake_mcp_client.databases["recommendations"][result["migration_recommendation_id"]]
    assert doc["program_id"] == "PAYROLL01"


def test_audit_event_written_for_recommendation(fake_mcp_client, make_fake_llm_client):
    llm = make_fake_llm_client([VALID_RECOMMENDATION])
    run_migration_recommendation(
        project_id="acme-2026",
        job_run_id="jr-1",
        agent_task_id="task-1",
        cobol_program_structure=STRUCTURE,
        mcp_client=fake_mcp_client,
        llm_client=llm,
    )
    assert len(fake_mcp_client.audit_events) == 1
    assert fake_mcp_client.audit_events[0]["action"] == "created_recommendation"
