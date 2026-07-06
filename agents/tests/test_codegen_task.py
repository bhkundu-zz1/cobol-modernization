import pytest

from agents.codegen.eligibility import ApprovalGateError
from agents.codegen.task import run_codegen
from agents.common.guardrails_client import GuardrailRejection

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
    "plain_english_summary": "PAYROLL01 reads employee records and calculates gross pay with overtime.",
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
    "plain_english_summary": "TIMESHEET reads timesheet records and validates days worked.",
}

STRUCTURE_NO_SUMMARY = {
    "type": "cobol_program_structure",
    "_id": "acme-2026:sf-c:cobol_program_structure",
    "source_file_id": "sf-c",
    "program_id": "NOSUMMARY",
    "copybooks_referenced": [],
    "call_graph": {"nodes": [], "edges": []},
    "paragraphs": [],
    "confidence_score": 0.9,
    "needs_human_review": False,
}

RECOMMENDATION_A_APPROVED = {
    "type": "migration_recommendation",
    "subject_type": "cobol_program",
    "subject_id": "acme-2026:sf-a:cobol_program_structure",
    "program_id": "PAYROLL01",
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
    "human_review_status": "approved",
}

RECOMMENDATION_B_PENDING = {
    "type": "migration_recommendation",
    "subject_type": "cobol_program",
    "subject_id": "acme-2026:sf-b:cobol_program_structure",
    "program_id": "TIMESHEET",
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
    "human_review_status": "pending",
}

RECOMMENDATION_NO_SUMMARY_APPROVED = {
    "type": "migration_recommendation",
    "subject_type": "cobol_program",
    "subject_id": "acme-2026:sf-c:cobol_program_structure",
    "program_id": "NOSUMMARY",
    "source_file_id": "sf-c",
    "job_run_id": "jr-3",
    "recommended_target": "python_microservice",
    "rationale": "n/a",
    "confidence_score": 0.9,
    "decision_factors": {},
    "alternative_considered": {"target": "java_spring_boot", "why_rejected": "n/a"},
    "risk_flags": [],
    "produced_by_agent": "recommendation-agent@v1",
    "produced_by_model": "mock",
    "human_review_status": "approved",
}

STORY_A = {
    "type": "story",
    "_id": "story-a",
    "epic_id": "epic-1",
    "title": "Extract PAYROLL01 gross-pay calc",
    "description": "...",
    "acceptance_criteria": ["References paragraph 1000-MAIN"],
    "source_program_ids": ["PAYROLL01"],
    "confidence_score": 0.9,
    "generated_by_agent": "epic-story-writer@v1",
    "edited_by_human": False,
    "edit_history_ref": [],
    "export_status": "not_exported",
}

STORY_MULTI_PROGRAM_MIXED_APPROVAL = {
    "type": "story",
    "_id": "story-mixed",
    "epic_id": "epic-1",
    "title": "Extract payroll + timesheet",
    "description": "...",
    "acceptance_criteria": ["References paragraph 1000-MAIN"],
    "source_program_ids": ["PAYROLL01", "TIMESHEET"],
    "confidence_score": 0.9,
    "generated_by_agent": "epic-story-writer@v1",
    "edited_by_human": False,
    "edit_history_ref": [],
    "export_status": "not_exported",
}

STORY_NO_SUMMARY = {
    "type": "story",
    "_id": "story-no-summary",
    "epic_id": "epic-1",
    "title": "Extract NOSUMMARY",
    "description": "...",
    "acceptance_criteria": ["References paragraph X"],
    "source_program_ids": ["NOSUMMARY"],
    "confidence_score": 0.9,
    "generated_by_agent": "epic-story-writer@v1",
    "edited_by_human": False,
    "edit_history_ref": [],
    "export_status": "not_exported",
}

SOURCE_FILE_A = {
    "_id": "acme-2026:sf-a:source_file",
    "type": "source_file",
    "upload_batch_id": "batch-1",
    "filename": "PAYROLL01.CBL",
    "language": "cobol",
    "source_text": "IDENTIFICATION DIVISION. PAYROLL01.",
}

SOURCE_FILE_C = {
    "_id": "acme-2026:sf-c:source_file",
    "type": "source_file",
    "upload_batch_id": "batch-3",
    "filename": "NOSUMMARY.CBL",
    "language": "cobol",
    "source_text": "IDENTIFICATION DIVISION. NOSUMMARY.",
}

PYTHON_CODEGEN_OUTPUT = {
    "files": [
        {"relative_path": "app/main.py", "content": "print('hello')"},
        {"relative_path": "requirements.txt", "content": "fastapi"},
    ],
    "entry_point": "app/main.py",
    "summary": "Generated a small FastAPI service.",
}

JAVA_CODEGEN_OUTPUT = {
    "files": [
        {"relative_path": "src/main/java/com/migration/payroll01/PayrollApplication.java", "content": "public class PayrollApplication {}"},
        {"relative_path": "pom.xml", "content": "<project></project>"},
    ],
    "entry_point": "src/main/java/com/migration/payroll01/PayrollApplication.java",
    "base_package": "com.migration.payroll01",
    "summary": "Generated a small Spring Boot service.",
}


def _seed_common(fake_mcp_client, *, include_b: bool = False):
    fake_mcp_client.couchdb_write(
        database="parsed_structure", doc=dict(STRUCTURE_A), project_id=PROJECT_ID, created_by="test", trace_id="t"
    )
    fake_mcp_client.couchdb_write(
        database="recommendations", doc=dict(RECOMMENDATION_A_APPROVED), project_id=PROJECT_ID, created_by="test", trace_id="t"
    )
    fake_mcp_client.couchdb_write(
        database="sources", doc=dict(SOURCE_FILE_A), project_id=PROJECT_ID, created_by="test", trace_id="t"
    )
    if include_b:
        fake_mcp_client.couchdb_write(
            database="parsed_structure", doc=dict(STRUCTURE_B), project_id=PROJECT_ID, created_by="test", trace_id="t"
        )
        fake_mcp_client.couchdb_write(
            database="recommendations", doc=dict(RECOMMENDATION_B_PENDING), project_id=PROJECT_ID, created_by="test", trace_id="t"
        )


def _seed_story(fake_mcp_client, story: dict):
    fake_mcp_client.couchdb_write(database="backlog", doc=dict(story), project_id=PROJECT_ID, created_by="test", trace_id="t")


def test_disambiguates_duplicate_program_id_by_using_the_approved_recommendations_own_structure(
    fake_mcp_client, make_fake_llm_client
):
    """Regression: program_id is not unique per project (repeated uploads
    of the same program produce multiple structure/recommendation docs
    sharing one program_id, confirmed against real session data). A
    pending duplicate must never mask an approved one, and generation must
    read the structure the approved recommendation actually references
    (via subject_id), not an arbitrary same-program_id structure."""
    pending_duplicate_structure = {**STRUCTURE_A, "_id": "acme-2026:sf-a-dup:cobol_program_structure", "source_file_id": "sf-a-dup"}
    pending_duplicate_recommendation = {
        **RECOMMENDATION_A_APPROVED,
        "subject_id": "acme-2026:sf-a-dup:cobol_program_structure",
        "source_file_id": "sf-a-dup",
        "human_review_status": "pending",
    }
    fake_mcp_client.couchdb_write(
        database="parsed_structure", doc=pending_duplicate_structure, project_id=PROJECT_ID, created_by="test", trace_id="t"
    )
    fake_mcp_client.couchdb_write(
        database="recommendations", doc=pending_duplicate_recommendation, project_id=PROJECT_ID, created_by="test", trace_id="t"
    )
    _seed_common(fake_mcp_client)
    _seed_story(fake_mcp_client, STORY_A)
    llm = make_fake_llm_client([PYTHON_CODEGEN_OUTPUT])

    result = run_codegen(
        project_id=PROJECT_ID,
        job_run_id="jr-codegen-dup",
        agent_task_id="task-1",
        story_id="story-a",
        target_language="python",
        mcp_client=fake_mcp_client,
        llm_client=llm,
    )

    assert result["generated_code_repo_path"] == "story-a"
    story_doc = fake_mcp_client.databases["backlog"]["story-a"]
    assert story_doc["code_generation_status"] == "generated"


def test_generation_commits_files_via_mcp_and_updates_story_status(fake_mcp_client, make_fake_llm_client):
    _seed_common(fake_mcp_client)
    _seed_story(fake_mcp_client, STORY_A)
    llm = make_fake_llm_client([PYTHON_CODEGEN_OUTPUT])

    result = run_codegen(
        project_id=PROJECT_ID,
        job_run_id="jr-codegen-1",
        agent_task_id="task-1",
        story_id="story-a",
        target_language="python",
        mcp_client=fake_mcp_client,
        llm_client=llm,
    )

    assert result["story_id"] == "story-a"
    assert result["generated_code_repo_path"] == "story-a"
    assert result["generated_code_commit_sha"]
    assert result["generated_code_commit_url"]

    story_doc = fake_mcp_client.databases["backlog"]["story-a"]
    assert story_doc["code_generation_status"] == "generated"
    assert story_doc["code_generation_target"] == "python"
    assert story_doc["generated_code_repo_path"] == "story-a"
    assert story_doc["generated_code_commit_sha"]
    assert story_doc["generated_code_commit_url"]
    assert story_doc["code_generation_error"] is None

    assert len(fake_mcp_client.codegen_commits) == 1
    commit_call = fake_mcp_client.codegen_commits[0]
    assert commit_call["story_id"] == "story-a"
    committed_paths = {f["relative_path"] for f in commit_call["files"]}
    assert committed_paths == {"app/main.py", "requirements.txt"}


def test_job_run_checkpoint_exists_before_any_llm_call(fake_mcp_client, make_fake_llm_client):
    _seed_common(fake_mcp_client)
    _seed_story(fake_mcp_client, STORY_A)
    llm = make_fake_llm_client([PYTHON_CODEGEN_OUTPUT])

    original_complete_json = llm.complete_json
    checkpoint_existed_before_first_call = {"value": None}

    def spying_complete_json(*args, **kwargs):
        if checkpoint_existed_before_first_call["value"] is None:
            checkpoint_existed_before_first_call["value"] = (
                f"{PROJECT_ID}:jr-codegen-1:job_run" in fake_mcp_client.databases.get("agent_runs", {})
            )
        return original_complete_json(*args, **kwargs)

    llm.complete_json = spying_complete_json

    run_codegen(
        project_id=PROJECT_ID,
        job_run_id="jr-codegen-1",
        agent_task_id="task-1",
        story_id="story-a",
        target_language="python",
        mcp_client=fake_mcp_client,
        llm_client=llm,
    )

    assert checkpoint_existed_before_first_call["value"] is True
    job_run_doc = fake_mcp_client.databases["agent_runs"][f"{PROJECT_ID}:jr-codegen-1:job_run"]
    assert job_run_doc["status"] == "completed"


def test_approval_gate_enforced_server_side_for_multi_program_story(fake_mcp_client, make_fake_llm_client):
    """One program approved, one pending -> generation must be blocked
    entirely, with no LLM call and no codegen_commit_files call."""
    _seed_common(fake_mcp_client, include_b=True)
    _seed_story(fake_mcp_client, STORY_MULTI_PROGRAM_MIXED_APPROVAL)
    llm = make_fake_llm_client([])  # no LLM call should happen

    with pytest.raises(ApprovalGateError):
        run_codegen(
            project_id=PROJECT_ID,
            job_run_id="jr-codegen-2",
            agent_task_id="task-1",
            story_id="story-mixed",
            target_language="python",
            mcp_client=fake_mcp_client,
            llm_client=llm,
        )

    assert llm.calls == []
    assert fake_mcp_client.codegen_commits == []


def test_missing_plain_english_summary_blocks_generation(fake_mcp_client, make_fake_llm_client):
    fake_mcp_client.couchdb_write(
        database="parsed_structure", doc=dict(STRUCTURE_NO_SUMMARY), project_id=PROJECT_ID, created_by="test", trace_id="t"
    )
    fake_mcp_client.couchdb_write(
        database="recommendations", doc=dict(RECOMMENDATION_NO_SUMMARY_APPROVED), project_id=PROJECT_ID, created_by="test", trace_id="t"
    )
    fake_mcp_client.couchdb_write(
        database="sources", doc=dict(SOURCE_FILE_C), project_id=PROJECT_ID, created_by="test", trace_id="t"
    )
    _seed_story(fake_mcp_client, STORY_NO_SUMMARY)
    llm = make_fake_llm_client([])

    with pytest.raises(ValueError, match="plain_english_summary"):
        run_codegen(
            project_id=PROJECT_ID,
            job_run_id="jr-codegen-3",
            agent_task_id="task-1",
            story_id="story-no-summary",
            target_language="python",
            mcp_client=fake_mcp_client,
            llm_client=llm,
        )

    assert llm.calls == []
    assert fake_mcp_client.codegen_commits == []


def test_java_target_selects_java_skill_and_commits_java_files(fake_mcp_client, make_fake_llm_client):
    _seed_common(fake_mcp_client)
    _seed_story(fake_mcp_client, STORY_A)
    llm = make_fake_llm_client([JAVA_CODEGEN_OUTPUT])

    result = run_codegen(
        project_id=PROJECT_ID,
        job_run_id="jr-codegen-4",
        agent_task_id="task-1",
        story_id="story-a",
        target_language="java_spring_boot",
        mcp_client=fake_mcp_client,
        llm_client=llm,
    )

    assert result["generated_code_repo_path"] == "story-a"
    committed_paths = {f["relative_path"] for f in fake_mcp_client.codegen_commits[0]["files"]}
    assert "pom.xml" in committed_paths
    story_doc = fake_mcp_client.databases["backlog"]["story-a"]
    assert story_doc["code_generation_target"] == "java_spring_boot"


def test_guardrail_rejection_when_generated_file_path_attempts_traversal(fake_mcp_client, make_fake_llm_client):
    malicious_output = {
        "files": [
            {"relative_path": "../../etc/passwd", "content": "x"},
            {"relative_path": "requirements.txt", "content": "fastapi"},
        ],
        "entry_point": "requirements.txt",
        "summary": "malicious",
    }
    _seed_common(fake_mcp_client)
    _seed_story(fake_mcp_client, STORY_A)
    # GuardrailRejection retries once via retry_fn before raising, so the
    # fake needs the malicious response queued twice.
    llm = make_fake_llm_client([malicious_output, malicious_output])

    with pytest.raises(GuardrailRejection):
        run_codegen(
            project_id=PROJECT_ID,
            job_run_id="jr-codegen-5",
            agent_task_id="task-1",
            story_id="story-a",
            target_language="python",
            mcp_client=fake_mcp_client,
            llm_client=llm,
        )

    # The malicious output is rejected by the guardrail before any commit
    # is attempted at all.
    assert fake_mcp_client.codegen_commits == []


def test_manifest_file_required_for_python_target(fake_mcp_client, make_fake_llm_client):
    missing_manifest_output = {
        "files": [{"relative_path": "app/main.py", "content": "print('hi')"}],
        "entry_point": "app/main.py",
        "summary": "no manifest",
    }
    _seed_common(fake_mcp_client)
    _seed_story(fake_mcp_client, STORY_A)
    llm = make_fake_llm_client([missing_manifest_output, missing_manifest_output])

    with pytest.raises(GuardrailRejection):
        run_codegen(
            project_id=PROJECT_ID,
            job_run_id="jr-codegen-7",
            agent_task_id="task-1",
            story_id="story-a",
            target_language="python",
            mcp_client=fake_mcp_client,
            llm_client=llm,
        )
