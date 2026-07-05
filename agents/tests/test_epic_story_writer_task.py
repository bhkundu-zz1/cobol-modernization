from agents.common.guardrails_client import GuardrailRejection
from agents.epic_story_writer.task import run_epic_story_generation

PROJECT_ID = "acme-2026"

STRUCTURE_A = {
    "type": "cobol_program_structure",
    "_id": "acme-2026:sf-a:cobol_program_structure",
    "source_file_id": "sf-a",
    "program_id": "PAYROLL01",
    "copybooks_referenced": ["EMPREC"],
    "call_graph": {"nodes": ["1000-MAIN"], "edges": []},
    "paragraphs": [{"name": "1000-MAIN", "calls": [], "performs": ["2000-CALC-GROSS"]}],
    "confidence_score": 0.9,
    "needs_human_review": False,
}

STRUCTURE_B = {
    "type": "cobol_program_structure",
    "_id": "acme-2026:sf-b:cobol_program_structure",
    "source_file_id": "sf-b",
    "program_id": "TIMESHEET",
    "copybooks_referenced": ["EMPREC"],
    "call_graph": {"nodes": ["1000-MAIN"], "edges": []},
    "paragraphs": [{"name": "1000-MAIN", "calls": [], "performs": []}],
    "confidence_score": 0.6,
    "needs_human_review": True,
}

RECOMMENDATION_A = {
    "type": "migration_recommendation",
    "subject_type": "cobol_program",
    "subject_id": "acme-2026:sf-a:cobol_program_structure",
    "source_file_id": "sf-a",
    "job_run_id": "jr-1",
    "recommended_target": "python_microservice",
    "rationale": "low complexity",
    "confidence_score": 0.85,
    "decision_factors": {},
    "alternative_considered": {"target": "java_spring_boot", "why_rejected": "n/a"},
    "risk_flags": [],
    "produced_by_agent": "recommendation-agent@v1",
    "produced_by_model": "mock",
}

RECOMMENDATION_B = {
    "type": "migration_recommendation",
    "subject_type": "cobol_program",
    "subject_id": "acme-2026:sf-b:cobol_program_structure",
    "source_file_id": "sf-b",
    "job_run_id": "jr-2",
    "recommended_target": "python_microservice",
    "rationale": "shares copybook with PAYROLL01",
    "confidence_score": 0.95,
    "decision_factors": {},
    "alternative_considered": {"target": "java_spring_boot", "why_rejected": "n/a"},
    "risk_flags": [],
    "produced_by_agent": "recommendation-agent@v1",
    "produced_by_model": "mock",
}

UNDERSTANDING_A = {"summary": "PAYROLL01 reads employee records and calculates gross pay with overtime."}
UNDERSTANDING_B = {"summary": "TIMESHEET reads timesheet records and validates days worked."}
EPIC_LLM_OUTPUT = {"title": "Payroll subsystem", "description": "Groups payroll and timesheet processing."}
STORY_LLM_OUTPUT_A = {
    "title": "Extract PAYROLL01 gross-pay calc",
    "description": "...",
    "acceptance_criteria": ["References paragraph 1000-MAIN"],
}
STORY_LLM_OUTPUT_B = {
    "title": "Extract TIMESHEET processing",
    "description": "...",
    "acceptance_criteria": ["References paragraph 1000-MAIN"],
}


def _seed_recommendations_and_structures(fake_mcp_client):
    for structure in (STRUCTURE_A, STRUCTURE_B):
        fake_mcp_client.couchdb_write(
            database="parsed_structure", doc=dict(structure), project_id=PROJECT_ID, created_by="test", trace_id="t"
        )
    for recommendation in (RECOMMENDATION_A, RECOMMENDATION_B):
        fake_mcp_client.couchdb_write(
            database="recommendations", doc=dict(recommendation), project_id=PROJECT_ID, created_by="test", trace_id="t"
        )


def _seed_source_files(fake_mcp_client):
    for source_file_id, text in (("sf-a", "IDENTIFICATION DIVISION. PAYROLL01."), ("sf-b", "IDENTIFICATION DIVISION. TIMESHEET.")):
        fake_mcp_client.couchdb_write(
            database="sources",
            doc={"_id": f"{PROJECT_ID}:{source_file_id}:source_file", "type": "source_file", "source_text": text},
            project_id=PROJECT_ID,
            created_by="test",
            trace_id="t",
        )


def test_shared_copybook_programs_grouped_into_one_epic(fake_mcp_client, make_fake_llm_client):
    _seed_recommendations_and_structures(fake_mcp_client)
    _seed_source_files(fake_mcp_client)
    llm = make_fake_llm_client([UNDERSTANDING_A, UNDERSTANDING_B, EPIC_LLM_OUTPUT, STORY_LLM_OUTPUT_A, STORY_LLM_OUTPUT_B])

    result = run_epic_story_generation(
        project_id=PROJECT_ID, job_run_id="jr-epic", agent_task_id="task-1", mcp_client=fake_mcp_client, llm_client=llm
    )

    assert result["clusters"] == 1
    assert len(result["epic_ids"]) == 1
    assert len(result["story_ids"]) == 2

    epic_doc = fake_mcp_client.databases["backlog"][result["epic_ids"][0]]
    assert epic_doc["title"] == "Payroll subsystem"

    story_docs = [fake_mcp_client.databases["backlog"][sid] for sid in result["story_ids"]]
    assert all(s["epic_id"] == result["epic_ids"][0] for s in story_docs)
    assert {s["source_program_ids"][0] for s in story_docs} == {"PAYROLL01", "TIMESHEET"}


def test_job_run_checkpoint_exists_before_any_llm_call(fake_mcp_client, make_fake_llm_client):
    """GET /jobs/{id} 404s until the job_run doc's first write. With real
    (slow) LLM calls this task can run for minutes, so the checkpoint must
    exist before the first LLM call, not only after the task completes --
    otherwise a status-polling caller sees nothing but 404s the whole time."""
    _seed_recommendations_and_structures(fake_mcp_client)
    _seed_source_files(fake_mcp_client)
    llm = make_fake_llm_client([UNDERSTANDING_A, UNDERSTANDING_B, EPIC_LLM_OUTPUT, STORY_LLM_OUTPUT_A, STORY_LLM_OUTPUT_B])

    original_complete_json = llm.complete_json
    checkpoint_existed_before_first_call = {"value": None}

    def spying_complete_json(*args, **kwargs):
        if checkpoint_existed_before_first_call["value"] is None:
            checkpoint_existed_before_first_call["value"] = (
                f"{PROJECT_ID}:jr-epic:job_run" in fake_mcp_client.databases.get("agent_runs", {})
            )
        return original_complete_json(*args, **kwargs)

    llm.complete_json = spying_complete_json

    run_epic_story_generation(
        project_id=PROJECT_ID, job_run_id="jr-epic", agent_task_id="task-1", mcp_client=fake_mcp_client, llm_client=llm
    )

    assert checkpoint_existed_before_first_call["value"] is True
    job_run_doc = fake_mcp_client.databases["agent_runs"][f"{PROJECT_ID}:jr-epic:job_run"]
    assert job_run_doc["status"] == "completed"


def test_understanding_persisted_onto_structure_doc(fake_mcp_client, make_fake_llm_client):
    _seed_recommendations_and_structures(fake_mcp_client)
    _seed_source_files(fake_mcp_client)
    llm = make_fake_llm_client([UNDERSTANDING_A, UNDERSTANDING_B, EPIC_LLM_OUTPUT, STORY_LLM_OUTPUT_A, STORY_LLM_OUTPUT_B])

    run_epic_story_generation(
        project_id=PROJECT_ID, job_run_id="jr-epic", agent_task_id="task-1", mcp_client=fake_mcp_client, llm_client=llm
    )

    structure_a = fake_mcp_client.databases["parsed_structure"][STRUCTURE_A["_id"]]
    structure_b = fake_mcp_client.databases["parsed_structure"][STRUCTURE_B["_id"]]
    assert structure_a["plain_english_summary"] == UNDERSTANDING_A["summary"]
    assert structure_b["plain_english_summary"] == UNDERSTANDING_B["summary"]


def test_existing_summary_is_reused_without_a_new_llm_call(fake_mcp_client, make_fake_llm_client):
    _seed_recommendations_and_structures(fake_mcp_client)
    _seed_source_files(fake_mcp_client)
    # Pre-populate PAYROLL01's summary directly on the seeded doc so the
    # understanding stage should skip it (only TIMESHEET needs summarizing).
    fake_mcp_client.databases["parsed_structure"][STRUCTURE_A["_id"]]["plain_english_summary"] = "already understood"

    llm = make_fake_llm_client([UNDERSTANDING_B, EPIC_LLM_OUTPUT, STORY_LLM_OUTPUT_A, STORY_LLM_OUTPUT_B])

    result = run_epic_story_generation(
        project_id=PROJECT_ID, job_run_id="jr-epic", agent_task_id="task-1", mcp_client=fake_mcp_client, llm_client=llm
    )

    assert len(result["story_ids"]) == 2
    assert len(llm.calls) == 4  # 1 understanding (B only) + 1 epic + 2 stories
    actions = [event["action"] for event in fake_mcp_client.audit_events]
    assert actions.count("created_code_understanding") == 1


def test_epic_confidence_capped_by_lowest_member_confidence(fake_mcp_client, make_fake_llm_client):
    _seed_recommendations_and_structures(fake_mcp_client)
    _seed_source_files(fake_mcp_client)
    llm = make_fake_llm_client([UNDERSTANDING_A, UNDERSTANDING_B, EPIC_LLM_OUTPUT, STORY_LLM_OUTPUT_A, STORY_LLM_OUTPUT_B])

    result = run_epic_story_generation(
        project_id=PROJECT_ID, job_run_id="jr-epic", agent_task_id="task-1", mcp_client=fake_mcp_client, llm_client=llm
    )

    epic_doc = fake_mcp_client.databases["backlog"][result["epic_ids"][0]]
    # min(structure_confidence, recommendation_confidence) per program:
    # PAYROLL01 -> min(0.9, 0.85) = 0.85; TIMESHEET -> min(0.6, 0.95) = 0.6
    # epic confidence is the min across its stories -> 0.6
    assert epic_doc["confidence_score"] == 0.6


def test_story_confidence_capped_by_its_own_program(fake_mcp_client, make_fake_llm_client):
    _seed_recommendations_and_structures(fake_mcp_client)
    _seed_source_files(fake_mcp_client)
    llm = make_fake_llm_client([UNDERSTANDING_A, UNDERSTANDING_B, EPIC_LLM_OUTPUT, STORY_LLM_OUTPUT_A, STORY_LLM_OUTPUT_B])

    result = run_epic_story_generation(
        project_id=PROJECT_ID, job_run_id="jr-epic", agent_task_id="task-1", mcp_client=fake_mcp_client, llm_client=llm
    )

    story_docs = {
        s["source_program_ids"][0]: s for s in (fake_mcp_client.databases["backlog"][sid] for sid in result["story_ids"])
    }
    assert story_docs["PAYROLL01"]["confidence_score"] == 0.85
    assert story_docs["TIMESHEET"]["confidence_score"] == 0.6


def test_unrelated_program_becomes_its_own_single_program_epic(fake_mcp_client, make_fake_llm_client):
    structure_c = {
        "type": "cobol_program_structure",
        "_id": "acme-2026:sf-c:cobol_program_structure",
        "source_file_id": "sf-c",
        "program_id": "REPORTGEN",
        "copybooks_referenced": [],
        "call_graph": {"nodes": [], "edges": []},
        "paragraphs": [],
        "confidence_score": 1.0,
        "needs_human_review": False,
    }
    recommendation_c = {**RECOMMENDATION_A, "subject_id": structure_c["_id"], "source_file_id": "sf-c"}
    fake_mcp_client.couchdb_write(
        database="parsed_structure", doc=structure_c, project_id=PROJECT_ID, created_by="test", trace_id="t"
    )
    fake_mcp_client.couchdb_write(
        database="recommendations", doc=recommendation_c, project_id=PROJECT_ID, created_by="test", trace_id="t"
    )
    fake_mcp_client.couchdb_write(
        database="sources",
        doc={"_id": f"{PROJECT_ID}:sf-c:source_file", "type": "source_file", "source_text": "IDENTIFICATION DIVISION. REPORTGEN."},
        project_id=PROJECT_ID,
        created_by="test",
        trace_id="t",
    )

    llm = make_fake_llm_client(
        [{"summary": "REPORTGEN prints a standalone report."}, {"title": "Report generation", "description": "Standalone."}, STORY_LLM_OUTPUT_A]
    )

    result = run_epic_story_generation(
        project_id=PROJECT_ID, job_run_id="jr-epic", agent_task_id="task-1", mcp_client=fake_mcp_client, llm_client=llm
    )

    assert result["clusters"] == 1
    assert len(result["story_ids"]) == 1


def test_audit_events_written_for_understanding_epic_and_story(fake_mcp_client, make_fake_llm_client):
    _seed_recommendations_and_structures(fake_mcp_client)
    _seed_source_files(fake_mcp_client)
    llm = make_fake_llm_client([UNDERSTANDING_A, UNDERSTANDING_B, EPIC_LLM_OUTPUT, STORY_LLM_OUTPUT_A, STORY_LLM_OUTPUT_B])

    run_epic_story_generation(
        project_id=PROJECT_ID, job_run_id="jr-epic", agent_task_id="task-1", mcp_client=fake_mcp_client, llm_client=llm
    )

    actions = [event["action"] for event in fake_mcp_client.audit_events]
    assert actions.count("created_code_understanding") == 2
    assert actions.count("created_epic") == 1
    assert actions.count("created_story") == 2


def test_guardrail_rejection_propagates_when_epic_output_missing_fields(fake_mcp_client, make_fake_llm_client):
    _seed_recommendations_and_structures(fake_mcp_client)
    _seed_source_files(fake_mcp_client)
    incomplete_epic_output = {"title": "Payroll subsystem"}  # missing "description"
    llm = make_fake_llm_client(
        [UNDERSTANDING_A, UNDERSTANDING_B, incomplete_epic_output, incomplete_epic_output]  # epic call + 1 retry, both bad
    )

    try:
        run_epic_story_generation(
            project_id=PROJECT_ID,
            job_run_id="jr-epic",
            agent_task_id="task-1",
            mcp_client=fake_mcp_client,
            llm_client=llm,
        )
        assert False, "expected GuardrailRejection"
    except GuardrailRejection:
        pass

    assert fake_mcp_client.databases.get("backlog", {}) == {}


def test_guardrail_rejection_when_understanding_summary_exceeds_600_words(fake_mcp_client, make_fake_llm_client):
    _seed_recommendations_and_structures(fake_mcp_client)
    _seed_source_files(fake_mcp_client)
    too_long = {"summary": " ".join(["word"] * 601)}
    llm = make_fake_llm_client([too_long, too_long])  # understanding call + 1 retry, both bad

    try:
        run_epic_story_generation(
            project_id=PROJECT_ID,
            job_run_id="jr-epic",
            agent_task_id="task-1",
            mcp_client=fake_mcp_client,
            llm_client=llm,
        )
        assert False, "expected GuardrailRejection"
    except GuardrailRejection:
        pass

    assert fake_mcp_client.databases.get("backlog", {}) == {}


def test_guardrail_rejection_when_epic_title_exceeds_50_words(fake_mcp_client, make_fake_llm_client):
    _seed_recommendations_and_structures(fake_mcp_client)
    _seed_source_files(fake_mcp_client)
    too_long_title = {"title": " ".join(["word"] * 51), "description": "fine"}
    llm = make_fake_llm_client([UNDERSTANDING_A, UNDERSTANDING_B, too_long_title, too_long_title])

    try:
        run_epic_story_generation(
            project_id=PROJECT_ID,
            job_run_id="jr-epic",
            agent_task_id="task-1",
            mcp_client=fake_mcp_client,
            llm_client=llm,
        )
        assert False, "expected GuardrailRejection"
    except GuardrailRejection:
        pass

    assert fake_mcp_client.databases.get("backlog", {}) == {}


def test_no_recommendations_produces_no_clusters(fake_mcp_client, make_fake_llm_client):
    llm = make_fake_llm_client([])

    result = run_epic_story_generation(
        project_id=PROJECT_ID, job_run_id="jr-epic", agent_task_id="task-1", mcp_client=fake_mcp_client, llm_client=llm
    )

    assert result == {"epic_ids": [], "story_ids": [], "clusters": 0}
