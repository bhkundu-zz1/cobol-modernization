"""Calls the LiteLLM proxy by logical model name (architecture.md section 4),
wrapping every call with guardrails_client.check_input/check_output
(architecture.md section 5's mandatory path: agent -> guardrails input rail
-> LiteLLM -> provider -> guardrails output rail -> agent).

Skills reference a logical model name (e.g. "cobol-analysis-dev") in their
frontmatter, never a literal provider string — litellm_config.yaml resolves
that name to an actual model/endpoint.
"""

import json
import os
from typing import Any

import httpx

from . import guardrails_client


def _extract_json_object(content: str) -> str:
    """Some providers (e.g. Anthropic via LiteLLM) wrap JSON-mode output in a
    ```json ... ``` fence and/or add leading/trailing prose instead of
    returning bare JSON. Extract the outermost {...} object by brace-matching
    so json.loads works regardless of which model produced the response."""
    start = content.find("{")
    if start == -1:
        return content.strip()
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(content)):
        char = content[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start : index + 1]
    return content.strip()


class LLMClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout: float = 60.0) -> None:
        self.base_url = (base_url or os.environ.get("LITELLM_PROXY_URL", "http://localhost:4000")).rstrip("/")
        self.api_key = api_key or os.environ.get("LITELLM_MASTER_KEY", "")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def complete_json(
        self,
        model: str,
        prompt: str,
        *,
        project_id: str,
        job_run_id: str,
    ) -> dict[str, Any]:
        """Sends `prompt` to `model` (a logical LiteLLM model name) and
        parses the response as JSON. Guardrails input/output rails wrap the
        call per architecture.md section 5."""
        screened_prompt = guardrails_client.check_input(prompt, project_id=project_id, job_run_id=job_run_id)

        response = self._client.post(
            "/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
            json={
                "model": model,
                "messages": [{"role": "user", "content": screened_prompt}],
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(_extract_json_object(content))


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
