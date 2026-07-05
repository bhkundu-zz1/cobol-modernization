from pathlib import Path

from agents.ingestion_chunking.chunker import build_chunks, chunking_required, classify_language

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "sample_cobol" / "PAYROLL01.CBL"


def test_fixture_classified_as_cobol_program():
    text = FIXTURE.read_text(encoding="utf-8")
    assert classify_language("PAYROLL01.CBL", text) == "cobol_program"


def test_fixture_under_chunking_threshold():
    text = FIXTURE.read_text(encoding="utf-8")
    line_count = len(text.splitlines())
    assert line_count < 100
    assert chunking_required(line_count) is False


def test_fixture_produces_no_chunks():
    text = FIXTURE.read_text(encoding="utf-8")
    assert build_chunks(text) == []


def test_large_file_is_chunked():
    lines = []
    for i in range(20):
        lines.append(f"{i:04d}-PARA-{i}.")
        lines.extend([f"    MOVE {i} TO WS-FIELD-{i}."] * 50)
    large_text = "\n".join(lines)

    assert chunking_required(len(large_text.splitlines())) is True
    chunks = build_chunks(large_text)
    assert len(chunks) > 1

    covered_lines = set()
    for chunk in chunks:
        covered_lines.update(range(chunk["start_line"], chunk["end_line"] + 1))
    assert max(covered_lines) >= len(large_text.splitlines()) - 1
