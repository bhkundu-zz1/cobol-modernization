from agents.common.confidence import cap_recommendation_confidence, compute_structural_confidence


def test_single_chunk_no_discrepancies_is_high_confidence():
    score, needs_review = compute_structural_confidence(
        chunks_used=1,
        discrepancies_found=0,
        any_discrepancy_unresolved=False,
        unresolved_external_call_count=0,
    )
    assert score == 1.0
    assert needs_review is False


def test_more_chunks_lowers_confidence():
    score, _ = compute_structural_confidence(
        chunks_used=7,
        discrepancies_found=0,
        any_discrepancy_unresolved=False,
        unresolved_external_call_count=0,
    )
    assert score < 1.0


def test_unresolved_discrepancy_forces_human_review_regardless_of_score():
    score, needs_review = compute_structural_confidence(
        chunks_used=1,
        discrepancies_found=1,
        any_discrepancy_unresolved=True,
        unresolved_external_call_count=0,
    )
    assert needs_review is True


def test_unresolved_external_call_penalizes_score():
    score_with, _ = compute_structural_confidence(
        chunks_used=1, discrepancies_found=0, any_discrepancy_unresolved=False, unresolved_external_call_count=1
    )
    score_without, _ = compute_structural_confidence(
        chunks_used=1, discrepancies_found=0, any_discrepancy_unresolved=False, unresolved_external_call_count=0
    )
    assert score_with < score_without


def test_recommendation_confidence_capped_by_structure_confidence():
    assert cap_recommendation_confidence(0.95, 0.6) == 0.6
    assert cap_recommendation_confidence(0.5, 0.9) == 0.5
