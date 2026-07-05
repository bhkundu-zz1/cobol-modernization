"""Minimal OpenAI-chat-completions-compatible mock LLM server.

Real, runnable FastAPI app — not a stub. Lets the vertical slice
(docker-compose up) run end-to-end with zero commercial/OSS API keys: the
`cobol-analysis-dev` LiteLLM model_list entry points here instead of at
Ollama, so `agents/common/llm_client.py` never needs a live model provider
to demo the pipeline.

Response strategy: inspect the incoming prompt (LiteLLM forwards our
agents' prompts verbatim) for known phrases from
agents/cobol_structural/prompts.py and agents/recommendation/task.py, and
return a plausible, schema-correct JSON completion for that specific
extraction/self-check/recommendation prompt shape. This is deliberately
simple pattern matching, not an actual model — good enough to prove the
pipeline's plumbing (chunking -> extraction -> merge -> self-check ->
confidence -> recommendation -> review queue) end-to-end.
"""

import json
import os
import time
import uuid

from fastapi import FastAPI, Request

app = FastAPI(title="Mock LLM Server")


def _extraction_response() -> dict:
    return {
        "program_id": "PAYROLL01",
        "divisions": {"identification": {}, "environment": {}, "data": {}, "procedure": {}},
        "copybooks_referenced": ["PAYRATES"],
        "paragraphs": [{"name": "1000-MAIN", "calls": [], "performs": ["2000-CALC-GROSS"]}],
        "external_calls": [{"target": "SUBRTN99", "call_type": "CALL", "resolved": False}],
        "uncertain_items": [],
    }


def _self_check_response() -> dict:
    return {"discrepancies_found": 0, "discrepancies": [], "resolved": True}


def _recommendation_response() -> dict:
    return {
        "recommended_target": "python_microservice",
        "rationale": (
            "Low structural complexity (one main paragraph, one calculation paragraph), "
            "no evidence of heavy state management or tight latency requirements."
        ),
        "confidence_score": 0.9,
        "alternative_considered": {
            "target": "java_spring_boot",
            "why_rejected": "no evidence of enterprise integration complexity or existing JVM investment "
            "that would justify the added operational overhead",
        },
        "risk_flags": ["unresolved external CALL to rate-lookup routine — target service must confirm data source before cutover"],
    }


def _understanding_response() -> dict:
    return {
        "summary": (
            "This program processes employee payroll records one at a time from a "
            "sequential file. For each employee, it looks up the current hourly pay "
            "rate by calling an external routine (SUBRTN99) that is not defined "
            "anywhere in this program or its copybook — that dependency is external "
            "and unverified, a real risk to flag before migration. Once the hourly "
            "rate is known, the program calculates gross pay: employees who worked "
            "more than 40 hours get their first 40 hours at the standard rate and "
            "the remaining hours at 1.5 times that rate (standard overtime rules); "
            "employees at or under 40 hours are paid at the standard rate for all "
            "hours worked. The program reads records until it reaches the end of "
            "the file, then stops. In short: it's a straightforward per-employee "
            "gross-pay calculator whose main external risk is the unresolved "
            "rate-lookup dependency."
        )
    }


def _epic_response() -> dict:
    return {
        "title": "Payroll subsystem migration",
        "description": (
            "Groups COBOL programs that share the PAYRATES copybook or call each other, "
            "migrated together since they participate in the same payroll data flow."
        ),
    }


def _story_response() -> dict:
    return {
        "title": "Extract program logic into the recommended target platform",
        "description": "Migrate this program's procedure division logic per the accompanying recommendation.",
        "acceptance_criteria": [
            "References paragraph 1000-MAIN: main control flow is preserved",
            "References paragraph 2000-CALC-GROSS: gross-pay calculation logic matches the original COBOL",
        ],
    }


def _route_prompt(prompt: str) -> dict:
    lowered = prompt.lower()
    if "self-check" in lowered or "identify any paragraphs" in lowered:
        return _self_check_response()
    if "recommending a migration target" in lowered:
        return _recommendation_response()
    if "experienced cobol programmer explaining" in lowered:
        return _understanding_response()
    if "naming a migration epic" in lowered:
        return _epic_response()
    if "drafting a user story" in lowered:
        return _story_response()
    if "extracting the structural shape" in lowered:
        return _extraction_response()
    # Fallback: echo an empty-but-valid extraction shape so unrecognized
    # prompts still get parseable JSON rather than a hard failure.
    return _extraction_response()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "mock-llm"}


@app.post("/chat/completions")
async def chat_completions(request: Request) -> dict:
    body = await request.json()
    messages = body.get("messages", [])
    prompt = messages[-1]["content"] if messages else ""
    content = json.dumps(_route_prompt(prompt))

    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.get("model", "mock-echo"),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": len(prompt.split()), "completion_tokens": len(content.split()), "total_tokens": 0},
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("MOCK_LLM_PORT", 9000)))
