from __future__ import annotations

from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.review import (
    ClaimReview,
    LLMReviewResult,
    ReviewFinding,
    ReviewSeverity,
    validate_review_result,
)


def test_llm_review_contract_is_provider_neutral_and_flags_claims() -> None:
    engine = GenesisEngine.from_spec(GenesisExperimentSpec(tick_count=1))
    engine.run_ticks()
    request = engine.build_review_request()
    result = LLMReviewResult(
        request_digest=request.digest(),
        reviewer_id="fake-reviewer",
        findings=(ReviewFinding(ReviewSeverity.HIGH, "Do not claim AGI."),),
        claim_review=ClaimReview(allowed=True),
    )
    validated = validate_review_result(result, request=request)
    assert not validated.claim_review.allowed
    assert "AGI" in validated.claim_review.flagged_claims
    assert validated.digest()
