"""Recommendation document models (architecture.md section 2.2)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from .envelope import DocEnvelope


class AlternativeConsidered(BaseModel):
    target: str
    why_rejected: str


class MigrationRecommendation(DocEnvelope):
    type: Literal["migration_recommendation"] = "migration_recommendation"
    subject_type: Literal["cobol_program", "jcl_job"]
    subject_id: str
    subject_filename: str | None = None
    source_file_id: str | None = None
    program_id: str | None = None
    job_run_id: str
    recommended_target: Literal[
        "java_spring_boot",
        "python_microservice",
        "python_airflow_dag",
        "python_cron_script",
    ]
    rationale: str
    confidence_score: float
    decision_factors: dict
    alternative_considered: AlternativeConsidered
    risk_flags: list[str]
    produced_by_agent: str
    produced_by_model: str
    human_review_status: Literal["pending", "approved", "rejected", "edited"] = "pending"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class RiskAssessment(DocEnvelope):
    """Schema-complete; unused by real logic this pass."""

    type: Literal["risk_assessment"] = "risk_assessment"
    subject_id: str
    risks: list[dict] = []
