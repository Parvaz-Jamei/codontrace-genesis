"""Phase J replay-verified CI candidate packs (measurement-first).

These tests document software capability. They do not claim intelligence,
collective intelligence, Tokyo Type 1 passed, or Avida replacement.
"""

from __future__ import annotations

import pytest

import codontrace.genesis as g
from codontrace.errors import ConfigurationError
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.phase_i import (
    RESEARCH_GENERATION_COUNT,
    RESEARCH_SEED_COUNT,
    SMOKE_GENERATION_COUNT,
    SMOKE_SEED_COUNT,
    TaskGroupEvaluation,
    earn_collective_intelligence_candidate_flags,
    run_evolved_division_of_labor_experiment,
    run_heldout_unfamiliar_partner_experiment,
    run_mls_evolutionary_outcome_experiment,
)
from codontrace.genesis.phase_j import (
    EVOLVED_DOL_KIND,
    HELD_OUT_KIND,
    MLS_KIND,
    CampaignReplaySpec,
    build_replay_verified_ci_candidate_pack,
    capture_campaign_replay,
    population_covariance,
    price_partition_from_groups,
    run_price_equation_covariance_scaffold,
    verify_digest_replay,
)
from codontrace.genesis.rag import load_default_corpus, search_corpus
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

LIFE_LOOP_SPEC_DIGEST = "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"
FORBIDDEN = (
    "intelligence",
    "collective_intelligence",
    "agi",
    "tokyo_type1_passed",
    "avida_replacement",
)


def _assert_forbidden(payload: dict[str, object]) -> None:
    gate = ScientificClaimGate()
    for label in FORBIDDEN:
        assert gate.decide(ClaimRequest(label, payload)).allowed is False


def test_phase_a_life_loop_digest_pin_unchanged_by_phase_j() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST


def test_rag_corpus_includes_price_1970() -> None:
    corpus = load_default_corpus()
    assert len(corpus) >= 15
    ids = {item.doc_id for item in corpus.documents()}
    assert "price_1970_selection_and_covariance" in ids
    assert "okasha_2006_levels_of_selection" in ids
    assert corpus.digest() == load_default_corpus().digest()
    hits = search_corpus("Price equation covariance selection Okasha MLS1 partition", k=5)
    assert any("price" in hit.document.doc_id for hit in hits.hits)


def test_price_partition_identity_on_hand_built_groups() -> None:
    group_low = TaskGroupEvaluation(
        preferences=(0.0, 0.0),
        tasks=("A", "A"),
        personal_fitness=(1.0, 1.0),
        group_fitness=0.0,
        n_task_a=2,
        n_task_b=0,
        nmi=0.0,
    )
    group_high = TaskGroupEvaluation(
        preferences=(1.0, 1.0),
        tasks=("B", "B"),
        personal_fitness=(3.0, 3.0),
        group_fitness=0.0,
        n_task_a=0,
        n_task_b=2,
        nmi=0.0,
    )
    partition = price_partition_from_groups((group_low, group_high))
    assert population_covariance((1.0, 1.0, 3.0, 3.0), (0.0, 0.0, 1.0, 1.0)) == 0.5
    assert partition.between_group_covariance_mls1 == 0.5
    assert partition.within_group_covariance == 0.0
    assert partition.total_organism_covariance == 0.5
    assert abs(partition.mls1_partition_residual) <= 1e-8
    assert partition.transmission_term_estimated is False
    assert partition.price_equation_complete is False
    assert partition.major_transition_in_individuality is False
    _assert_forbidden(partition.to_dict())


def test_price_scaffold_smoke_is_measured_and_does_not_earn_ci() -> None:
    campaign = run_price_equation_covariance_scaffold(smoke=True)
    payload = campaign.to_dict()
    assert len(campaign.seeds) == SMOKE_SEED_COUNT
    assert campaign.generations == SMOKE_GENERATION_COUNT
    assert campaign.price_equation_status == "measured_runtime_observation"
    assert campaign.mls1_identity_holds is True
    assert campaign.major_transition_in_individuality is False
    assert campaign.claim_gate_flags_auto_set is False
    assert payload["collective_intelligence"] is False
    _assert_forbidden(payload)
    with pytest.raises(ConfigurationError, match="at least two seeds"):
        run_price_equation_covariance_scaffold(seeds=(3,))


def test_same_object_replay_does_not_earn_replay_verification() -> None:
    campaign = run_heldout_unfamiliar_partner_experiment(smoke=True)
    spec = CampaignReplaySpec(
        kind=HELD_OUT_KIND,
        seeds=campaign.seeds,
        generations=campaign.generations,
        n_groups=4,
        group_size=4,
        smoke=True,
    )
    capture = capture_campaign_replay(HELD_OUT_KIND, campaign, spec)
    verification = verify_digest_replay([capture], replay_campaigns={HELD_OUT_KIND: campaign})
    assert verification.matched is True
    assert verification.re_executed is False
    assert verification.earns_replay_verification() is False
    assert any("replay_is_same_object" in item for item in verification.issues)
    earned = earn_collective_intelligence_candidate_flags(
        heldout=campaign, replay=verification, smoke=True
    )
    assert earned.as_mapping()["replay_verification"] is False


def test_mismatched_replay_digests_do_not_earn() -> None:
    first = run_evolved_division_of_labor_experiment(smoke=True, seeds=(11, 12))
    other = run_evolved_division_of_labor_experiment(smoke=True, seeds=(21, 22))
    spec = CampaignReplaySpec(
        kind=EVOLVED_DOL_KIND,
        seeds=first.seeds,
        generations=first.generations,
        n_groups=4,
        group_size=4,
        smoke=True,
    )
    capture = capture_campaign_replay(EVOLVED_DOL_KIND, first, spec)
    verification = verify_digest_replay([capture], replay_campaigns={EVOLVED_DOL_KIND: other})
    assert verification.matched is False
    assert verification.earns_replay_verification() is False
    assert any("digest_mismatch" in item for item in verification.issues)


def test_independent_smoke_replay_matches_but_smoke_never_earns() -> None:
    pack = build_replay_verified_ci_candidate_pack(
        smoke=True, re_execute_replay=True, include_price_equation=True
    )
    flags = pack.as_mapping()
    assert pack.replay.matched is True
    assert pack.replay.re_executed is True
    assert pack.replay.earns_replay_verification() is True
    assert pack.smoke is True
    assert all(value is False for value in flags.values())
    assert flags["replay_verification"] is False
    assert pack.candidate_allowed is False
    assert "replay_verification" in pack.candidate_missing_flags
    assert pack.price is not None
    assert pack.price.mls1_identity_holds is True
    _assert_forbidden(pack.to_dict())
    gate = ScientificClaimGate()
    assert gate.decide(ClaimRequest("collective_intelligence_candidate", flags)).allowed is False


def test_research_scale_honest_replay_can_allow_candidate_not_ci() -> None:
    pack = build_replay_verified_ci_candidate_pack(
        seed_count=RESEARCH_SEED_COUNT,
        generations=RESEARCH_GENERATION_COUNT,
        n_groups=4,
        smoke=False,
        re_execute_replay=True,
        include_price_equation=False,
    )
    flags = pack.as_mapping()
    assert pack.research_scale is True
    assert pack.replay.matched is True
    assert pack.replay.re_executed is True
    assert flags["heldout_protocol"] is True
    assert flags["role_complementarity"] is True
    assert flags["ablation_result"] is True
    assert flags["collective_report_digest"] is True
    assert flags["replay_verification"] is True
    gate = ScientificClaimGate()
    candidate = gate.decide(ClaimRequest("collective_intelligence_candidate", flags))
    assert candidate.allowed is True
    assert pack.candidate_allowed is True
    assert pack.candidate_missing_flags == ()
    _assert_forbidden(flags)
    _assert_forbidden(pack.to_dict())
    assert gate.decide(ClaimRequest("collective_intelligence", flags)).allowed is False


def test_no_replay_source_does_not_earn() -> None:
    mls = run_mls_evolutionary_outcome_experiment(smoke=True)
    spec = CampaignReplaySpec(
        kind=MLS_KIND,
        seeds=mls.seeds,
        generations=mls.generations,
        n_groups=4,
        group_size=4,
        smoke=True,
    )
    capture = capture_campaign_replay(MLS_KIND, mls, spec)
    verification = verify_digest_replay([capture], re_execute=False)
    assert verification.earns_replay_verification() is False
    assert "no_replay_source_supplied" in verification.issues


def test_phase_j_public_api_bindings() -> None:
    for name in (
        "build_replay_verified_ci_candidate_pack",
        "run_price_equation_covariance_scaffold",
        "verify_digest_replay",
        "capture_campaign_replay",
        "population_covariance",
        "price_partition_from_groups",
        "DigestReplayVerification",
        "ReplayVerifiedCiCandidatePack",
        "PriceEquationCovarianceCampaign",
        "CampaignReplaySpec",
        "CampaignReplayCapture",
        "evaluate_phase_j_claim",
    ):
        assert hasattr(g, name)
        assert name in g.__all__
