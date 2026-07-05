"""Builds the structured decision_factors payload
(agents/skills/migration-recommendation/SKILL.md, Step 1)."""

from typing import Any


def build_decision_factors(cobol_structure: dict[str, Any]) -> dict[str, Any]:
    paragraph_count = len(cobol_structure.get("paragraphs", []))
    call_graph = cobol_structure.get("call_graph", {})
    fan_out = len(call_graph.get("edges", []))
    external_call_count = len(cobol_structure.get("external_calls", []))

    complexity = "high" if paragraph_count > 20 or fan_out > 30 else "low" if paragraph_count <= 5 else "medium"

    return {
        "complexity": complexity,
        "paragraph_count": paragraph_count,
        "call_graph_fan_out": fan_out,
        "external_call_count": external_call_count,
        # These signals aren't derivable from a COBOL program's structure
        # alone this pass (no CICS/online-transaction detection, no
        # client-supplied skillset metadata yet) — left absent rather than
        # guessed, per the skill's "note its absence rather than defaulting
        # silently" instruction.
        "state_management": "unknown",
        "batch_vs_online": "unknown",
        "performance_sensitivity": "unknown",
        "integration_points": external_call_count,
    }
