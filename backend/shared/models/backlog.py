"""Epic/Story document models (architecture.md section 2.2).

Epic/Story generation (agents/epic_story_writer/task.py) is real — see
that module for the clustering/drafting logic. `confidence_score` on both
models is capped by the underlying cobol_program_structure/
migration_recommendation confidence (agents/common/confidence.py), so a
shaky structural extraction or recommendation propagates visibly into the
backlog rather than presenting manufactured certainty. The export
mechanism (Editor MFE + GitHub adapter + epic_story_service routes) is
also real and independent of generation.
"""

from typing import Literal

from .envelope import DocEnvelope

ExportTarget = Literal["jira", "github"]
CodeGenTarget = Literal["python", "java_spring_boot"]


class Epic(DocEnvelope):
    type: Literal["epic"] = "epic"
    title: str
    description: str
    confidence_score: float = 1.0
    export_target: ExportTarget | None = None
    external_milestone_id: str | None = None
    external_milestone_url: str | None = None


class Story(DocEnvelope):
    type: Literal["story"] = "story"
    epic_id: str
    title: str
    description: str
    acceptance_criteria: list[str] = []
    source_program_ids: list[str] = []
    confidence_score: float = 1.0
    generated_by_agent: str
    edited_by_human: bool = False
    edit_history_ref: list[str] = []
    export_status: Literal["not_exported", "exported"] = "not_exported"
    export_target: ExportTarget | None = None
    external_issue_key: str | None = None
    external_issue_url: str | None = None
    code_generation_status: Literal["not_generated", "generating", "generated", "failed"] = "not_generated"
    code_generation_target: CodeGenTarget | None = None
    code_generation_job_run_id: str | None = None
    generated_code_repo_path: str | None = None
    generated_code_commit_sha: str | None = None
    generated_code_commit_url: str | None = None
    code_generation_error: str | None = None
