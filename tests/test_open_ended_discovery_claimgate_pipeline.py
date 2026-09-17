"""Waves الف–د: open-ended discovery ClaimGate pipeline gates.

Does not claim AGI, collective intelligence, or open-ended proof.
Pins A–E must remain unchanged (knobs off / unrelated path).
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from codontrace.errors import ConfigurationError
from codontrace.genesis.discovery_campaign import (
    run_discovery_campaign,
    write_discovery_campaign_report,
)
from codontrace.genesis.discovery_runner import (
    hand_crafted_demo_candidates,
    run_discovery_pipeline,
)
from codontrace.genesis.discovery_witness import (
    CLAIM_CEILING_DISCOVERY_CANDIDATE,
    CLAIM_CEILING_RUNTIME,
    CandidateSpec,
    DiscoveryAuditReport,
)
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.novelty_proposer import (
    ArchiveSummary,
    ExternalModelStubProposer,
    NoveltyProposer,
    RandomProposer,
    empty_archive_summary,
    parse_external_proposal,
)
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.statistical_protocol import paired_effect_size

LIFE_LOOP_SPEC_DIGEST = "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"
LIFE_LOOP_SNAPSHOT_DIGEST = "76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a"


def test_phase_a_life_loop_digest_pin_unchanged_by_discovery_pipeline() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    replay = GenesisEngine.from_spec(spec).run_ticks()
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST
    assert result.digest() == replay.digest()
    assert result.snapshot.digest() == LIFE_LOOP_SNAPSHOT_DIGEST


def test_wave_alef_pipeline_accept_reject_on_hand_crafted_candidates() -> None:
    archive = ArchiveSummary(
        archive_digest="test_archive",
        filled_bins=3,
        coverage=0.2,
        best_fitness=0.4,
        mean_fitness=0.25,
        descriptor_names=("unique_positions", "energy_efficiency"),
        elite_genomes=("A", "B", "C"),
    )
    weak, mid, strong = hand_crafted_demo_candidates()
    weak_report = run_discovery_pipeline(weak, scale="S1", archive_summary=archive)
    mid_report = run_discovery_pipeline(mid, scale="S1", archive_summary=archive)
    strong_report = run_discovery_pipeline(strong, scale="S1", archive_summary=archive)

    assert weak_report.accepted is False
    assert weak_report.claim_ceiling == CLAIM_CEILING_RUNTIME
    assert mid_report.accepted is False
    assert mid_report.claim_ceiling == CLAIM_CEILING_RUNTIME
    assert strong_report.accepted is True
    assert strong_report.beat_all_negatives is True
    assert strong_report.claim_ceiling == CLAIM_CEILING_DISCOVERY_CANDIDATE
    for report in (weak_report, mid_report, strong_report):
        assert len(report.negative_controls) == 3
        assert {c.control_id for c in report.negative_controls} == {
            "proposer_random",
            "proposer_shuffled_archive",
            "archive_no_op",
        }
        assert report.digest() == DiscoveryAuditReport.from_dict(report.to_dict()).digest()


def test_wave_beh_novelty_proposer_protocol_and_stub_without_paid_api() -> None:
    archive = empty_archive_summary(digest="beh")
    random_p: NoveltyProposer = RandomProposer(seed=1)
    stub_p: NoveltyProposer = ExternalModelStubProposer(seed=2)
    a = random_p.propose(archive)
    b = stub_p.propose(archive)
    assert a.source == "proposer_random"
    assert b.source == "external_model_stub"
    assert b.metadata.get("paid_api") is False
    parsed = parse_external_proposal(
        {
            "candidate_id": "ext",
            "genome": "G",
            "descriptors": {"unique_positions": 0.5},
            "quality": 0.3,
            "source": "external",
            "metadata": {"note": "boundary"},
        }
    )
    assert parsed.candidate_id == "ext"
    with pytest.raises(ConfigurationError):
        parse_external_proposal({"genome": "missing_id"})


def test_wave_jim_witness_sha256_matches_content() -> None:
    candidate = CandidateSpec(
        candidate_id="w1",
        genome="G",
        descriptors={"x": 1.0},
        quality=0.5,
        source="hand_crafted",
    )
    assert candidate.digest() == CandidateSpec.from_dict(candidate.to_dict()).digest()
    report = run_discovery_pipeline(candidate, scale="S1")
    assert report.digest() == DiscoveryAuditReport.from_dict(report.to_dict()).digest()
    for control in report.negative_controls:
        assert control.digest() == control.__class__.from_dict(control.to_dict()).digest()


def test_wave_dal_campaign_three_to_five_with_honest_rates(tmp_path: Path) -> None:
    report = run_discovery_campaign(scale="S1", max_proposals=5)
    assert 3 <= report.proposal_count <= 5
    assert report.accept_count + report.reject_count == report.proposal_count
    assert report.reject_rate == pytest.approx(report.reject_count / report.proposal_count)
    # Honesty: do not require accepts; 100% reject is valid.
    assert 0.0 <= report.accept_rate <= 1.0
    assert report.claim_ceiling == CLAIM_CEILING_RUNTIME or report.beat_all_negatives_count > 0
    json_path = tmp_path / "campaign.json"
    md_path = tmp_path / "campaign.md"
    write_discovery_campaign_report(report, json_path=json_path, markdown_path=md_path)
    assert json_path.is_file()
    assert "reject" in md_path.read_text(encoding="utf-8").lower()


@given(
    value=st.sampled_from([0.0, 1.0, -1.0, 2.5, -3.25, 10.0]),
    n=st.integers(min_value=2, max_value=64),
)
def test_paired_effect_size_never_returns_nan_when_variance_zero(value: float, n: int) -> None:
    """Exact zero-variance deltas must not yield NaN (return 0.0 or raise)."""

    deltas = [value] * n
    mean = sum(deltas) / len(deltas)
    sample_sd = math.sqrt(sum((item - mean) ** 2 for item in deltas) / (len(deltas) - 1))
    assert sample_sd == 0.0
    if mean == 0.0:
        result = paired_effect_size(deltas)
        assert result == 0.0
        assert not math.isnan(result)
    else:
        with pytest.raises(ConfigurationError, match="undefined"):
            paired_effect_size(deltas)
