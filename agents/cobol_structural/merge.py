"""Cross-chunk call-graph stitching (agents/skills/cobol-structural-analysis/SKILL.md, Step 2)."""

from typing import Any


def merge_chunk_extractions(extractions: list[dict[str, Any]]) -> dict[str, Any]:
    """Stitches per-chunk extraction dicts (each matching the extraction
    prompt's output shape) into one assembled structure. Single-chunk input
    is the common case for small programs and passes through unchanged
    except for call_graph construction."""
    program_id = next((e.get("program_id") for e in extractions if e.get("program_id")), None)

    copybooks: set[str] = set()
    paragraphs_by_name: dict[str, dict[str, Any]] = {}
    external_calls: list[dict[str, Any]] = []
    uncertain_items: list[str] = []

    for extraction in extractions:
        copybooks.update(extraction.get("copybooks_referenced", []))
        uncertain_items.extend(extraction.get("uncertain_items", []))
        external_calls.extend(extraction.get("external_calls", []))

        for paragraph in extraction.get("paragraphs", []):
            name = paragraph["name"]
            existing = paragraphs_by_name.get(name)
            if existing is None or len(paragraph.get("calls", [])) + len(paragraph.get("performs", [])) > len(
                existing.get("calls", [])
            ) + len(existing.get("performs", [])):
                paragraphs_by_name[name] = paragraph

    paragraphs = list(paragraphs_by_name.values())
    nodes = list(paragraphs_by_name.keys()) + [c["target"] for c in external_calls]
    edges = []
    for paragraph in paragraphs:
        for target in paragraph.get("calls", []) + paragraph.get("performs", []):
            edges.append({"from": paragraph["name"], "to": target})

    # Cross-chunk stitches: an edge whose target isn't itself a known
    # paragraph or external call target is the highest-risk case tracked by
    # the confidence scorer via "chunks_used", not counted separately here.
    return {
        "program_id": program_id,
        "divisions": extractions[0].get("divisions", {}) if extractions else {},
        "copybooks_referenced": sorted(copybooks),
        "paragraphs": paragraphs,
        "call_graph": {"nodes": sorted(set(nodes)), "edges": edges, "confidence": 1.0 if len(extractions) == 1 else 0.8},
        "external_calls": external_calls,
        "uncertain_items": uncertain_items,
    }
