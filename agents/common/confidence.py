"""Shared confidence-score computation (architecture.md section 3.4).

Used by both the COBOL structural agent and the recommendation agent.
Starts from a baseline, penalized by chunk count (more chunks = more
cross-chunk stitching risk), self-check discrepancy count, and count of
unresolved external calls / unfound copybooks.
"""

BASELINE_CONFIDENCE = 1.0
CHUNK_PENALTY_PER_CHUNK = 0.03
DISCREPANCY_PENALTY = 0.1
UNRESOLVED_CALL_PENALTY = 0.05
NEEDS_REVIEW_THRESHOLD = 0.7


def compute_structural_confidence(
    *,
    chunks_used: int,
    discrepancies_found: int,
    any_discrepancy_unresolved: bool,
    unresolved_external_call_count: int,
) -> tuple[float, bool]:
    """Returns (confidence_score, needs_human_review)."""
    score = BASELINE_CONFIDENCE
    score -= max(0, chunks_used - 1) * CHUNK_PENALTY_PER_CHUNK
    score -= discrepancies_found * DISCREPANCY_PENALTY
    score -= unresolved_external_call_count * UNRESOLVED_CALL_PENALTY
    score = max(0.0, min(1.0, score))

    needs_human_review = score < NEEDS_REVIEW_THRESHOLD
    if any_discrepancy_unresolved:
        needs_human_review = True

    return round(score, 3), needs_human_review


def cap_recommendation_confidence(recommendation_confidence: float, input_structure_confidence: float) -> float:
    """A recommendation can't be more certain than the structural facts it's
    based on (architecture.md's migration-recommendation skill, Step 3)."""
    return round(min(recommendation_confidence, input_structure_confidence), 3)
