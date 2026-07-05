import pytest
from pydantic import BaseModel

from agents.common.guardrails_client import GuardrailRejection, check_output


class Recommendation(BaseModel):
    rationale: str
    alternative_considered: dict
    risk_flags: list[str]


def test_check_output_passes_valid_payload():
    payload = {
        "rationale": "low complexity, no heavy state",
        "alternative_considered": {"target": "java_spring_boot", "why_rejected": "no JVM investment"},
        "risk_flags": ["unresolved external call"],
    }
    validated = check_output(payload, Recommendation, project_id="acme-2026", job_run_id="jr-1")
    assert validated.rationale == payload["rationale"]


def test_check_output_rejects_missing_required_field_with_no_retry():
    payload = {"rationale": "x"}  # missing alternative_considered, risk_flags
    with pytest.raises(GuardrailRejection):
        check_output(payload, Recommendation, project_id="acme-2026", job_run_id="jr-1", max_retries=0)


def test_check_output_retries_and_succeeds_on_corrective_reprompt():
    bad_payload = {"rationale": "x"}
    good_payload = {
        "rationale": "corrected",
        "alternative_considered": {"target": "python_microservice", "why_rejected": "n/a"},
        "risk_flags": [],
    }

    calls = {"count": 0}

    def retry_fn():
        calls["count"] += 1
        return good_payload

    validated = check_output(
        bad_payload, Recommendation, project_id="acme-2026", job_run_id="jr-1", retry_fn=retry_fn, max_retries=1
    )
    assert validated.rationale == "corrected"
    assert calls["count"] == 1


def test_check_output_exhausts_retries_and_raises():
    bad_payload = {"rationale": "x"}

    def retry_fn():
        return bad_payload  # still invalid

    with pytest.raises(GuardrailRejection):
        check_output(
            bad_payload, Recommendation, project_id="acme-2026", job_run_id="jr-1", retry_fn=retry_fn, max_retries=2
        )
