"""Asserts the chain/chord structure and argument wiring, without a real
Celery worker or broker — Celery signatures can be introspected without
executing them."""

from orchestrator.pipeline import build_pipeline, build_recommendation_group, build_structural_group


def test_build_pipeline_produces_three_step_chain():
    pipeline = build_pipeline(
        project_id="acme-2026",
        job_run_id="jr-1",
        upload_batch_id="batch-1",
        source_file_id="sf-1",
        filename="PAYROLL01.CBL",
        source_text="IDENTIFICATION DIVISION.\nPROGRAM-ID. PAYROLL01.",
        source_origin="manual_upload",
    )
    tasks = pipeline.tasks
    assert len(tasks) == 3
    assert tasks[0].task == "agents.ingestion_chunking.task.run_ingestion"
    assert tasks[1].task == "agents.cobol_structural.task.run_cobol_structural"
    assert tasks[2].task == "agents.recommendation.task.run_recommendation"


def test_ingestion_and_structural_steps_are_immutable_signatures():
    pipeline = build_pipeline(
        project_id="acme-2026",
        job_run_id="jr-1",
        upload_batch_id="batch-1",
        source_file_id="sf-1",
        filename="PAYROLL01.CBL",
        source_text="IDENTIFICATION DIVISION.",
        source_origin="manual_upload",
    )
    # immutable=True signatures don't accept the previous task's return value
    assert pipeline.tasks[0].immutable is True
    assert pipeline.tasks[1].immutable is True
    # the recommendation step IS mutable: it receives run_cobol_structural's
    # result as its first positional arg
    assert pipeline.tasks[2].immutable is False


def test_recommendation_signature_carries_project_and_job_run_ids():
    pipeline = build_pipeline(
        project_id="acme-2026",
        job_run_id="jr-1",
        upload_batch_id="batch-1",
        source_file_id="sf-1",
        filename="PAYROLL01.CBL",
        source_text="IDENTIFICATION DIVISION.",
        source_origin="manual_upload",
    )
    recommendation_sig = pipeline.tasks[2]
    assert recommendation_sig.args == ("acme-2026", "jr-1", recommendation_sig.args[2])


def test_build_structural_group_includes_cobol_and_jcl_branches():
    cobol_files = [{"source_file_id": "sf-1", "source_text": "IDENTIFICATION DIVISION."}]
    jcl_files = [{"source_file_id": "sf-2"}]
    grp = build_structural_group("acme-2026", "jr-1", cobol_files, jcl_files)
    task_names = [sig.task for sig in grp.tasks]
    assert "agents.cobol_structural.task.run_cobol_structural" in task_names
    assert "agents.jcl_structural.task.run_jcl_structural" in task_names


def test_build_structural_group_tolerates_empty_jcl_list():
    cobol_files = [{"source_file_id": "sf-1", "source_text": "IDENTIFICATION DIVISION."}]
    grp = build_structural_group("acme-2026", "jr-1", cobol_files, [])
    assert len(grp.tasks) == 1


def test_build_recommendation_group_one_task_per_structure():
    structural_results = [
        {"cobol_program_structure_id": "acme-2026:sf-1:cobol_program_structure"},
        {"cobol_program_structure_id": "acme-2026:sf-2:cobol_program_structure"},
    ]
    grp = build_recommendation_group("acme-2026", "jr-1", structural_results)
    assert len(grp.tasks) == 2
    assert all(sig.task == "agents.recommendation.task.run_recommendation" for sig in grp.tasks)
    assert grp.tasks[0].args[0] == structural_results[0]
