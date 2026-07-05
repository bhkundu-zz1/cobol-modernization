"""Regex-based secret/PII pre-pass (agents/skills/ingestion-chunking/SKILL.md, Step 1).

The regex pass is cheap and deterministic; a model-classification pass for
ambiguous candidates is intentionally not implemented this pass (it would
call llm_client per-candidate) — the regex coverage below is what actually
runs, matching the fixture's benign content correctly.
"""

import re

_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credential_literal": re.compile(
        r"\b(PASSWORD|PWD|APIKEY|SECRET)\b\s*(PIC|VALUE)\s+.*['\"]\S+['\"]", re.IGNORECASE
    ),
    "private_key_block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}


def scan_source_text(text: str) -> list[str]:
    """Returns a list of pattern names that matched (empty if none)."""
    return [name for name, pattern in _PATTERNS.items() if pattern.search(text)]


def build_secret_scan_result(filename_to_text: dict[str, str]) -> dict:
    flagged_files = [filename for filename, text in filename_to_text.items() if scan_source_text(text)]
    return {"flagged_files": flagged_files, "scan_passed": len(flagged_files) == 0}
