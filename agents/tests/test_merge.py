from agents.cobol_structural.merge import merge_chunk_extractions


def test_single_extraction_passthrough():
    extraction = {
        "program_id": "PAYROLL01",
        "divisions": {"identification": {}, "environment": {}, "data": {}, "procedure": {}},
        "copybooks_referenced": ["PAYRATES"],
        "paragraphs": [{"name": "1000-MAIN", "calls": [], "performs": ["2000-CALC-GROSS"]}],
        "external_calls": [{"target": "SUBRTN99", "call_type": "CALL", "resolved": False}],
        "uncertain_items": [],
    }
    merged = merge_chunk_extractions([extraction])
    assert merged["program_id"] == "PAYROLL01"
    assert merged["call_graph"]["confidence"] == 1.0
    assert {"from": "1000-MAIN", "to": "2000-CALC-GROSS"} in merged["call_graph"]["edges"]


def test_multi_chunk_merge_dedupes_paragraphs_and_unions_copybooks():
    chunk1 = {
        "program_id": "PAYROLL01",
        "divisions": {},
        "copybooks_referenced": ["EMPMASTR"],
        "paragraphs": [{"name": "1000-MAIN", "calls": [], "performs": []}],
        "external_calls": [],
        "uncertain_items": ["ambiguous boundary at chunk end"],
    }
    chunk2 = {
        "program_id": None,
        "divisions": {},
        "copybooks_referenced": ["PAYRATES"],
        "paragraphs": [{"name": "1000-MAIN", "calls": [], "performs": ["2000-CALC-GROSS"]}],
        "external_calls": [{"target": "SUBRTN99", "call_type": "CALL", "resolved": False}],
        "uncertain_items": [],
    }
    merged = merge_chunk_extractions([chunk1, chunk2])

    assert merged["program_id"] == "PAYROLL01"
    assert merged["copybooks_referenced"] == ["EMPMASTR", "PAYRATES"]
    assert len(merged["paragraphs"]) == 1, "duplicate paragraph across chunks should be deduped"
    assert merged["paragraphs"][0]["performs"] == ["2000-CALC-GROSS"], "should prefer the more-populated version"
    assert merged["call_graph"]["confidence"] == 0.8
    assert "ambiguous boundary at chunk end" in merged["uncertain_items"]
