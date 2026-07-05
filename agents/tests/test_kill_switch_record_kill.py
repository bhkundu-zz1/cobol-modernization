"""Regression test: when a Celery task is killed mid-flight, the outer
@shared_task wrapper must record the kill (agent_task checkpoint = "killed",
job_run.status = "killed") even though the pure function raised AgentKilled
before ever reaching its own write_checkpoint call. Confirmed as a live bug
during a kill-switch drill: job_run stayed stuck at "running" forever with
no record that a stage was actually killed."""

from agents.cobol_structural.task import run_cobol_structural
from agents.common.kill_switch import AgentKilled


def test_cobol_structural_records_kill_when_killed_before_first_checkpoint(fake_mcp_client, monkeypatch):
    fake_mcp_client.killed = True

    monkeypatch.setattr("agents.cobol_structural.task.get_mcp_client", lambda: fake_mcp_client)
    monkeypatch.setattr("orchestrator.checkpoint.get_mcp_client", lambda: fake_mcp_client)

    try:
        run_cobol_structural.run(
            project_id="acme-2026",
            job_run_id="jr-1",
            agent_task_id="task-1",
            source_file_id="sf-1",
            source_text="IDENTIFICATION DIVISION.",
        )
        assert False, "expected AgentKilled to propagate"
    except AgentKilled:
        pass

    job_run = fake_mcp_client.databases["agent_runs"]["acme-2026:jr-1:job_run"]
    assert job_run["status"] == "killed"

    agent_task = fake_mcp_client.databases["agent_runs"]["acme-2026:task-1:agent_task"]
    assert agent_task["status"] == "killed"
