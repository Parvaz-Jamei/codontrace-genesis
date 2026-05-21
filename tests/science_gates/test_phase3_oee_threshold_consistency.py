import pytest

from codontrace.genesis import canonical_digest
from codontrace.genesis.open_endedness import (
    LearnabilityReport,
    OEECandidateMetrics,
    OEE_RESEARCH_GRADE_MIN_SEEDS,
    SteppingStoneTransferReport,
)


def D(name: str) -> str:
    return canonical_digest({"oee": name})


def _metrics(seed_count: int) -> OEECandidateMetrics:
    return OEECandidateMetrics(
        novelty_persistence=1.0,
        behavioral_innovation_rate=1.0,
        lineage_depth_growth=1.0,
        archive_expansion=1.0,
        learnability_delta=1.0,
        complexity_growth_cost_adjusted=1.0,
        d0_baseline_distance=1.0,
        shadow_baseline_delta=1.0,
        ablation_sensitivity=1.0,
        multi_seed_count=seed_count,
        replay_verified=True,
        replay_digest=D("replay"),
        d0_baseline_digest=D("d0"),
        shadow_digest=D("shadow"),
    )


def test_oee_candidate_metrics_two_seed_is_not_claim_eligible():
    report = _metrics(2)
    assert report.evidence_level == "descriptive_only"
    assert not report.claim_eligible


def test_oee_candidate_metrics_requires_research_grade_seed_threshold_for_final_claim():
    assert not _metrics(OEE_RESEARCH_GRADE_MIN_SEEDS - 1).claim_eligible
    assert _metrics(OEE_RESEARCH_GRADE_MIN_SEEDS).claim_eligible


def test_learnability_report_not_run_digest_is_not_claim_eligible():
    report = LearnabilityReport(1.0, "not_run:heldout", "fake")
    assert not report.claim_eligible
    assert "missing_heldout_digest" in report.rejection_reasons
    assert "missing_replay_digest" in report.rejection_reasons


def test_stepping_stone_report_requires_real_transfer_and_replay_digest():
    weak = SteppingStoneTransferReport(1.0, "placeholder", D("replay"))
    strong = SteppingStoneTransferReport(1.0, D("heldout"), D("replay"))
    assert not weak.claim_eligible
    assert strong.claim_eligible
