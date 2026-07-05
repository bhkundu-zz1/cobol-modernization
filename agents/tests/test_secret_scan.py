from pathlib import Path

from agents.ingestion_chunking.secret_scan import build_secret_scan_result, scan_source_text

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "sample_cobol" / "PAYROLL01.CBL"


def test_fixture_has_no_flagged_patterns():
    text = FIXTURE.read_text(encoding="utf-8")
    assert scan_source_text(text) == []


def test_ssn_pattern_detected():
    text = "01 WS-SSN PIC X(11) VALUE '123-45-6789'."
    assert "ssn" in scan_source_text(text)


def test_credential_literal_detected():
    text = 'WS-PASSWORD PIC X(20) VALUE "hunter2secret".'
    assert "credential_literal" in scan_source_text(text)


def test_build_secret_scan_result_all_clean():
    result = build_secret_scan_result({"PAYROLL01.CBL": FIXTURE.read_text(encoding="utf-8")})
    assert result == {"flagged_files": [], "scan_passed": True}


def test_build_secret_scan_result_flags_bad_file():
    result = build_secret_scan_result(
        {
            "CLEAN.CBL": "IDENTIFICATION DIVISION.",
            "DIRTY.CBL": "01 WS-SSN PIC X(11) VALUE '123-45-6789'.",
        }
    )
    assert result["flagged_files"] == ["DIRTY.CBL"]
    assert result["scan_passed"] is False
