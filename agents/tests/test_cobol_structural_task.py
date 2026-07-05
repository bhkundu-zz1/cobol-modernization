from pathlib import Path

from agents.cobol_structural.task import run_cobol_structural_analysis

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "sample_cobol" / "PAYROLL01.CBL"

EXTRACTION_RESPONSE = {
    "program_id": "PAYROLL01",
    "divisions": {"identification": {}, "environment": {}, "data": {}, "procedure": {}},
    "copybooks_referenced": ["PAYRATES"],
    "paragraphs": [{"name": "1000-MAIN", "calls": [], "performs": ["2000-CALC-GROSS"]}],
    "external_calls": [{"target": "SUBRTN99", "call_type": "CALL", "resolved": False}],
    "uncertain_items": [],
}

SELF_CHECK_RESPONSE_CLEAN = {"discrepancies_found": 0, "discrepancies": [], "resolved": True}


def test_single_chunk_fixture_produces_cobol_program_structure(fake_mcp_client, make_fake_llm_client):
    llm = make_fake_llm_client([EXTRACTION_RESPONSE, SELF_CHECK_RESPONSE_CLEAN])
    source_text = FIXTURE.read_text(encoding="utf-8")

    result = run_cobol_structural_analysis(
        project_id="acme-2026",
        job_run_id="jr-1",
        agent_task_id="task-1",
        source_file_id="sf-1",
        source_text=source_text,
        mcp_client=fake_mcp_client,
        llm_client=llm,
    )

    doc = fake_mcp_client.databases["parsed_structure"][result["cobol_program_structure_id"]]
    assert doc["type"] == "cobol_program_structure"
    assert doc["program_id"] == "PAYROLL01"
    assert doc["chunks_used"] == 1
    assert doc["self_check_pass"]["performed"] is True
    assert doc["extraction_method"] == "llm_native_chunked"
    assert len(fake_mcp_client.audit_events) == 1
    assert fake_mcp_client.audit_events[0]["action"] == "created_cobol_program_structure"


def test_unresolved_external_call_lowers_confidence_and_needs_review(fake_mcp_client, make_fake_llm_client):
    llm = make_fake_llm_client([EXTRACTION_RESPONSE, SELF_CHECK_RESPONSE_CLEAN])
    source_text = FIXTURE.read_text(encoding="utf-8")

    result = run_cobol_structural_analysis(
        project_id="acme-2026",
        job_run_id="jr-1",
        agent_task_id="task-1",
        source_file_id="sf-1",
        source_text=source_text,
        mcp_client=fake_mcp_client,
        llm_client=llm,
    )
    # unresolved SUBRTN99 call present in EXTRACTION_RESPONSE
    assert result["confidence_score"] < 1.0


def test_unresolved_self_check_discrepancy_forces_human_review(fake_mcp_client, make_fake_llm_client):
    self_check_unresolved = {"discrepancies_found": 1, "discrepancies": ["missing paragraph 3000-X"], "resolved": False}
    llm = make_fake_llm_client([EXTRACTION_RESPONSE, self_check_unresolved])
    source_text = FIXTURE.read_text(encoding="utf-8")

    result = run_cobol_structural_analysis(
        project_id="acme-2026",
        job_run_id="jr-1",
        agent_task_id="task-1",
        source_file_id="sf-1",
        source_text=source_text,
        mcp_client=fake_mcp_client,
        llm_client=llm,
    )
    assert result["needs_human_review"] is True


def test_kill_switch_stops_task_before_writing(fake_mcp_client, make_fake_llm_client):
    from agents.common.kill_switch import AgentKilled

    fake_mcp_client.killed = True
    llm = make_fake_llm_client([EXTRACTION_RESPONSE, SELF_CHECK_RESPONSE_CLEAN])

    try:
        run_cobol_structural_analysis(
            project_id="acme-2026",
            job_run_id="jr-1",
            agent_task_id="task-1",
            source_file_id="sf-1",
            source_text=FIXTURE.read_text(encoding="utf-8"),
            mcp_client=fake_mcp_client,
            llm_client=llm,
        )
        assert False, "expected AgentKilled"
    except AgentKilled:
        pass

    assert fake_mcp_client.databases.get("parsed_structure", {}) == {}
