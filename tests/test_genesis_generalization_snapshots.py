from codontrace.genesis import canonical_digest
from codontrace.genesis.phase_b_scientific_maturity import HeldoutEvaluationResult


def D(name: str) -> str:
    return canonical_digest({"generalization": name})


def test_heldout_evaluation_requires_distinct_world_for_claim_eligibility():
    result = HeldoutEvaluationResult(
        "snap", D("source"), D("lineage"), D("world"), D("partner"),
        1, 2, "deterministic", "heldout_distinct", D("heldout"), 0.25,
    )
    assert result.claim_eligible
    assert result.digest() == HeldoutEvaluationResult(
        "snap", D("source"), D("lineage"), D("world"), D("partner"),
        1, 2, "deterministic", "heldout_distinct", D("heldout"), 0.25,
    ).digest()


def test_identical_train_heldout_seed_is_leakage_unless_explicit_control():
    result = HeldoutEvaluationResult(
        "snap", D("source"), D("lineage"), D("world"), D("partner"),
        1, 1, "deterministic", "heldout_distinct", D("heldout"), 0.0,
    )
    assert result.leakage_status == "leakage_detected"
    assert not result.claim_eligible


def test_not_run_heldout_digest_rejects_generalization_claim():
    result = HeldoutEvaluationResult(
        "snap", D("source"), D("lineage"), D("world"), D("partner"),
        1, 2, "deterministic", "heldout_distinct", "not_run:heldout", 0.0,
    )
    assert result.leakage_status == "heldout_not_run"
    assert not result.claim_eligible
