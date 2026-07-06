"""Required-field and schema_version validation tests for every shared document model."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from shared.models import (
    AgentTask,
    AuditActor,
    AuditEvent,
    Chunk,
    CobolProgramStructure,
    Epic,
    JobRun,
    MigrationRecommendation,
    SourceFile,
    SourceUpload,
    Story,
)

ENVELOPE_KWARGS = dict(
    project_id="acme-2026",
    created_by="user:bhakti.kundu@gmail.com",
    trace_id="trace-uuid",
)


def test_source_upload_requires_fields():
    doc = SourceUpload(
        **ENVELOPE_KWARGS,
        uploaded_by="user@client.com",
        upload_batch_id="batch-1",
        source_origin="manual_upload",
        file_count=1,
        total_bytes=100,
        status="received",
    )
    assert doc.type == "source_upload"
    assert doc.schema_version == 1
    assert doc.secret_scan_result.scan_passed is False

    with pytest.raises(ValidationError):
        SourceUpload(**ENVELOPE_KWARGS, uploaded_by="x")  # missing required fields


def test_source_file_scm_element_ref_optional():
    doc = SourceFile(
        **ENVELOPE_KWARGS,
        upload_batch_id="batch-1",
        filename="PAYROLL01.CBL",
        language="cobol",
        sha256="deadbeef",
        line_count=58,
        chunking_required=False,
        source_origin="manual_upload",
    )
    assert doc.scm_element_ref is None


def test_chunk_requires_line_range():
    with pytest.raises(ValidationError):
        Chunk(**ENVELOPE_KWARGS, source_file_id="sf-1")


def test_cobol_program_structure_defaults():
    doc = CobolProgramStructure(
        **ENVELOPE_KWARGS,
        source_file_id="sf-1",
        program_id="PAYROLL01",
        chunks_used=1,
        confidence_score=0.9,
        needs_human_review=False,
    )
    assert doc.extraction_method == "llm_native_chunked"
    assert doc.call_graph.confidence == 0.0
    assert doc.self_check_pass.performed is False
    assert doc.plain_english_summary is None


def test_cobol_program_structure_accepts_plain_english_summary():
    doc = CobolProgramStructure(
        **ENVELOPE_KWARGS,
        source_file_id="sf-1",
        program_id="PAYROLL01",
        chunks_used=1,
        confidence_score=0.9,
        needs_human_review=False,
        plain_english_summary="Reads employee records and calculates gross pay with overtime.",
    )
    assert doc.plain_english_summary == "Reads employee records and calculates gross pay with overtime."


def test_migration_recommendation_requires_alternative_and_risk_flags():
    doc = MigrationRecommendation(
        **ENVELOPE_KWARGS,
        subject_type="cobol_program",
        subject_id="cps-1",
        job_run_id="jr-1",
        recommended_target="python_microservice",
        rationale="low complexity, no heavy state",
        confidence_score=0.8,
        decision_factors={"complexity": "low"},
        alternative_considered={"target": "java_spring_boot", "why_rejected": "no JVM investment"},
        risk_flags=["unresolved external call"],
        produced_by_agent="recommendation-agent@v1",
        produced_by_model="cobol-analysis-dev",
    )
    assert doc.human_review_status == "pending"

    with pytest.raises(ValidationError):
        MigrationRecommendation(
            **ENVELOPE_KWARGS,
            subject_type="cobol_program",
            subject_id="cps-1",
            job_run_id="jr-1",
            recommended_target="python_microservice",
            rationale="x",
            confidence_score=0.8,
            decision_factors={},
            risk_flags=[],
            produced_by_agent="a",
            produced_by_model="m",
        )  # missing alternative_considered


def test_job_run_and_agent_task_status_literal():
    job_run = JobRun(
        **ENVELOPE_KWARGS,
        job_run_id="jr-1",
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    assert job_run.tasks == []

    with pytest.raises(ValidationError):
        JobRun(
            **ENVELOPE_KWARGS,
            job_run_id="jr-1",
            status="not-a-real-status",
            started_at=datetime.now(timezone.utc),
        )

    task = AgentTask(
        **ENVELOPE_KWARGS,
        job_run_id="jr-1",
        agent="cobol_structural",
        status="completed",
    )
    assert task.error is None


def test_audit_event_requires_hash_chain_fields():
    event = AuditEvent(
        **ENVELOPE_KWARGS,
        event_id="evt-1",
        event_category="agent_output",
        actor=AuditActor(kind="agent", id="cobol-structural@v1"),
        action="created_recommendation",
        subject_doc_id="doc-1",
        timestamp=datetime.now(timezone.utc),
        prev_event_hash="0" * 64,
        this_event_hash="1" * 64,
    )
    assert event.type == "audit_event"

    with pytest.raises(ValidationError):
        AuditEvent(
            **ENVELOPE_KWARGS,
            event_id="evt-1",
            event_category="agent_output",
            actor=AuditActor(kind="agent", id="x"),
            action="created_recommendation",
            subject_doc_id="doc-1",
            timestamp=datetime.now(timezone.utc),
        )  # missing prev_event_hash / this_event_hash


def test_backlog_shapes_construct_with_no_export_yet():
    epic = Epic(**ENVELOPE_KWARGS, title="Extract payroll", description="...")
    story = Story(
        **ENVELOPE_KWARGS,
        epic_id=epic.id or "epic-1",
        title="Extract gross-pay calc",
        description="...",
        generated_by_agent="epic-story-writer@v1",
    )
    assert story.export_status == "not_exported"
    assert story.export_target is None
    assert story.external_issue_key is None
    assert epic.export_target is None
    assert story.code_generation_status == "not_generated"
    assert story.code_generation_target is None
    assert story.generated_code_repo_path is None
    assert story.generated_code_commit_sha is None
    assert story.generated_code_commit_url is None
    assert story.code_generation_error is None


def test_story_records_code_generation_fields():
    story = Story(
        **ENVELOPE_KWARGS,
        epic_id="epic-1",
        title="Extract gross-pay calc",
        description="...",
        generated_by_agent="epic-story-writer@v1",
        code_generation_status="generated",
        code_generation_target="python",
        code_generation_job_run_id="jr-1",
        generated_code_repo_path="story-a",
        generated_code_commit_sha="abc123",
        generated_code_commit_url="https://github.com/acme-org/generated-migrations/commit/abc123",
    )
    assert story.code_generation_status == "generated"
    assert story.code_generation_target == "python"
    assert story.generated_code_repo_path == "story-a"
    assert story.generated_code_commit_sha == "abc123"
    assert story.generated_code_commit_url.endswith("/commit/abc123")
    assert story.code_generation_error is None


def test_epic_and_story_record_github_export_fields():
    epic = Epic(
        **ENVELOPE_KWARGS,
        title="Extract payroll",
        description="...",
        export_target="github",
        external_milestone_id="7",
        external_milestone_url="https://github.com/acme-org/payroll-modernization/milestone/7",
    )
    story = Story(
        **ENVELOPE_KWARGS,
        epic_id=epic.id or "epic-1",
        title="Extract gross-pay calc",
        description="...",
        generated_by_agent="epic-story-writer@v1",
        export_status="exported",
        export_target="github",
        external_issue_key="acme-org/payroll-modernization#42",
        external_issue_url="https://github.com/acme-org/payroll-modernization/issues/42",
    )
    assert epic.export_target == "github"
    assert story.export_status == "exported"
    assert story.external_issue_url.endswith("/issues/42")
