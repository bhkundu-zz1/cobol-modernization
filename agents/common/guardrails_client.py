"""Local guardrails stub with REAL schema validation (architecture.md section 5).

No real NeMo Guardrails container is called this pass — see
docs/deferred_scope.md. What IS real: check_output performs genuine
Pydantic/JSON-schema validation against the expected output shape,
rejecting/retrying on missing required fields exactly as the real output
rail would. The call-site order (input rail before the LLM call, output
rail after) is preserved so a real container can be swapped in later via
config alone.
"""

import logging
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger("guardrails_client")

T = TypeVar("T", bound=BaseModel)


class GuardrailRejection(Exception):
    """Raised when check_output's schema validation fails after all retries."""


def check_input(prompt: str, project_id: str, job_run_id: str) -> str:
    """Input rail: jailbreak/prompt-injection + PII/secret leakage screening
    on the outbound prompt (architecture.md section 5). Stubbed this pass —
    logs and passes the prompt through unchanged. A real NeMo Guardrails
    call would replace this function's body without changing its signature.
    """
    logger.info(
        "guardrails.check_input (stub, pass-through)",
        extra={"project_id": project_id, "job_run_id": job_run_id, "prompt_len": len(prompt)},
    )
    return prompt


def check_output(
    raw_output: dict[str, Any],
    schema: type[T],
    *,
    project_id: str,
    job_run_id: str,
    retry_fn: Callable[[], dict[str, Any]] | None = None,
    max_retries: int = 1,
) -> T:
    """Output rail: validates raw_output against `schema` (a Pydantic model),
    matching architecture.md section 5's "does the recommendation JSON have
    required fields" check. On failure, calls `retry_fn` (a corrective
    re-prompt) up to `max_retries` times before raising GuardrailRejection.

    This validation is real — it is the concrete implementation the
    guardrail's schema-compliance NFR (architecture.md section 9.2) needs,
    just not backed by an actual NeMo Guardrails container yet.
    """
    attempt_output = raw_output
    last_error: ValidationError | None = None

    for attempt in range(max_retries + 1):
        try:
            validated = schema.model_validate(attempt_output)
            logger.info(
                "guardrails.check_output passed",
                extra={"project_id": project_id, "job_run_id": job_run_id, "attempt": attempt},
            )
            return validated
        except ValidationError as exc:
            last_error = exc
            logger.warning(
                "guardrails.check_output failed validation",
                extra={
                    "project_id": project_id,
                    "job_run_id": job_run_id,
                    "attempt": attempt,
                    "errors": exc.errors(),
                },
            )
            if attempt < max_retries and retry_fn is not None:
                attempt_output = retry_fn()
            else:
                break

    raise GuardrailRejection(
        f"output failed schema validation against {schema.__name__} after "
        f"{max_retries + 1} attempt(s): {last_error}"
    )
