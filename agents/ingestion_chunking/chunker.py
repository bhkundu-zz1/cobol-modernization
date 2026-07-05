"""Paragraph/PROC-boundary-aware chunker (agents/skills/ingestion-chunking/SKILL.md, Step 3)."""

import re

COBOL_LINE_BUDGET = 800
OVERLAP_LINES = 15

_PARAGRAPH_HEADER = re.compile(r"^\s{0,6}[A-Z0-9][A-Z0-9-]*\.\s*$")


def classify_language(filename: str, text: str) -> str:
    if "IDENTIFICATION DIVISION" in text and "PROGRAM-ID" in text:
        return "cobol_program"
    if re.search(r"^//\S+\s+JOB\b", text, re.MULTILINE):
        return "jcl_job"
    if re.search(r"^\s*01\s+\S+", text, re.MULTILINE) and "PROGRAM-ID" not in text:
        return "copybook"
    return "cobol_program" if filename.upper().endswith(".CBL") else "jcl_job"


def chunking_required(line_count: int) -> bool:
    return line_count > COBOL_LINE_BUDGET


def _find_paragraph_boundaries(lines: list[str]) -> list[int]:
    return [i for i, line in enumerate(lines) if _PARAGRAPH_HEADER.match(line)]


def build_chunks(text: str) -> list[dict]:
    """Splits `text` into overlapping chunks at paragraph boundaries.
    Returns a list of dicts with chunk_index/of_chunks/start_line/end_line
    (1-indexed, inclusive) — caller attaches project_id/source_file_id etc.
    """
    lines = text.splitlines()
    if not chunking_required(len(lines)):
        return []

    boundaries = _find_paragraph_boundaries(lines) or list(range(0, len(lines), COBOL_LINE_BUDGET))
    chunk_starts = [b for b in boundaries if b % COBOL_LINE_BUDGET < COBOL_LINE_BUDGET] or [0]

    # Group boundaries into chunks of roughly COBOL_LINE_BUDGET lines each,
    # snapping chunk end points to the nearest paragraph boundary.
    chunks: list[tuple[int, int]] = []
    start = 0
    while start < len(lines):
        target_end = min(start + COBOL_LINE_BUDGET, len(lines))
        candidates = [b for b in boundaries if start < b <= target_end]
        end = candidates[-1] if candidates else target_end
        chunks.append((start, end))
        start = end

    results = []
    total = len(chunks)
    for idx, (start, end) in enumerate(chunks):
        overlap_start = max(0, start - OVERLAP_LINES)
        results.append(
            {
                "chunk_index": idx,
                "of_chunks": total,
                "chunk_strategy": "paragraph-boundary",
                "overlap_lines": OVERLAP_LINES if idx > 0 else 0,
                "start_line": overlap_start + 1,
                "end_line": end,
            }
        )
    return results
