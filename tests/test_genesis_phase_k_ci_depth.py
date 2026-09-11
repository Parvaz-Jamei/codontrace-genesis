"""Phase K literature-grade CI depth measurements (measurement-first).

These tests document software capability. They do not claim intelligence,
collective intelligence, Tokyo Type 1 passed, or Avida replacement.
"""

from __future__ import annotations

import pytest

import codontrace.genesis as g
from codontrace.errors import ConfigurationError
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.phase_i import (
    SMOKE_GENERATION_COUNT,
    SMOKE_SEED_COUNT,
    earn_collective_intelligence_candidate_flags,
)
from codontrace.genesis.phase_k import (
    COORDINATION_ISA,
    GOLDSBY_LITERATURE_DELAYS,
    GOLDSBY_RESEARCH_REPLICATE_COUNT,
    GOLDSBY_SMOKE_REPLICATE_COUNT,
    ISA_BROADCAST,
    ISA_NOP,
    ISA_RETRIEVE,
    ISA_SEND,
    ISA_WORK_A,
    ISA_WORK_B,
    ConflictSuppressionObservation,
    build_conflict_suppression_observation,
    evaluate_coordination_group,
    evaluate_phase_k_claim,
    measure_isolation_competence,
    run_cheater_invasion_assay,
    run_evolved_coordination_instruction_experiment,
    run_goldsby_cpu_delay_specialist_campaign,
    run_multi_generation_price_analysis,
    run_revertant_isolation_assay,
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


def test_phase_a_life_loop_digest_pin_unchanged_by_phase_k() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST


def test_rag_corpus_includes_phase_k_cites() -> None:
    corpus = load_default_corpus()
    assert len(corpus) >= 16
    ids = {item.doc_id for item in corpus.documents()}
    assert "price_1972_extension_covariance_selection" in ids
    assert "goldsby_ofria_avida_messaging_germline" in ids
    assert "goldsby_2012_pnas_task_switching" in ids
    assert "michod_2007_pnas_export_of_fitness" in ids
    assert "conlin_2023_dol_multicellularity_avida" in ids
    assert corpus.digest() == load_default_corpus().digest()
    hits = search_corpus(
        "evolved send retrieve broadcast coordination instructions that pay", k=6
    )
    assert any("goldsby" in hit.document.doc_id for hit in hits.hits)
    price = search_corpus("Price equation transmission term parent offspring", k=6)
    assert any("price" in hit.document.doc_id for hit in price.hits)
    conlin = search_corpus("Conlin revertant entrenchment conflict suppression", k=6)
    assert any(
        "conlin" in hit.document.doc_id or "michod" in hit.document.doc_id for hit in conlin.hits
    )


def test_hand_built_send_retrieve_pays_and_ablation_drops() -> None:
    sender = (ISA_WORK_A, ISA_SEND, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP)
    retriever = (ISA_NOP, ISA_NOP, ISA_RETRIEVE, ISA_WORK_B, ISA_NOP, ISA_NOP)
    paid = evaluate_coordination_group(
        (sender, retriever),
        messaging_enabled=True,
        organism_ids=("a", "b"),
        deme_id="pay",
    )
    ablated = evaluate_coordination_group(
        (sender, retriever),
        messaging_enabled=False,
        organism_ids=("a", "b"),
        deme_id="off",
    )
    assert paid.phase_e_message_count >= 1
    assert paid.successful_retrieve >= 1
    assert paid.coordination_payoff > 0.0
    assert paid.group_fitness > ablated.group_fitness
    assert ablated.coordination_payoff == 0.0
    assert ablated.successful_retrieve == 0
    _assert_forbidden(paid.to_dict())


def test_broadcast_can_pay_and_work_only_pair_has_no_coordination_bonus() -> None:
    broadcaster = (ISA_WORK_A, ISA_BROADCAST, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP)
    retriever = (ISA_NOP, ISA_NOP, ISA_RETRIEVE, ISA_WORK_B, ISA_NOP, ISA_NOP)
    paid = evaluate_coordination_group((broadcaster, retriever), messaging_enabled=True)
    workers = evaluate_coordination_group(
        (
            (ISA_WORK_A, ISA_WORK_A, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP),
            (ISA_WORK_B, ISA_WORK_B, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP),
        ),
        messaging_enabled=True,
    )
    assert paid.n_broadcast >= 1
    assert paid.coordination_payoff > 0.0
    assert workers.coordination_payoff == 0.0
    assert workers.complementary_payoff > 0.0


def test_cpu_delay_can_block_task_switching() -> None:
    generalist = (ISA_WORK_A, ISA_WORK_B, ISA_WORK_A, ISA_WORK_B, ISA_NOP, ISA_NOP)
    zero = evaluate_coordination_group((generalist,), messaging_enabled=False, cpu_delay_cycles=0)
    high = evaluate_coordination_group((generalist,), messaging_enabled=False, cpu_delay_cycles=50)
    assert zero.work_a_counts[0] > 0 and zero.work_b_counts[0] > 0
    assert high.work_b_counts[0] == 0 or high.personal_fitness[0] < zero.personal_fitness[0]


def test_evolved_coordination_smoke_is_measured_and_does_not_earn() -> None:
    with pytest.raises(ConfigurationError, match="at least two seeds"):
        run_evolved_coordination_instruction_experiment(seeds=(3,))
    campaign = run_evolved_coordination_instruction_experiment(smoke=True)
    payload = campaign.to_dict()
    assert len(campaign.seeds) == SMOKE_SEED_COUNT
    assert campaign.generations == SMOKE_GENERATION_COUNT
    assert campaign.uses_phase_e_messaging is True
    assert campaign.evolved_not_assigned is True
    assert campaign.uses_capsules is False
    assert campaign.claim_gate_flags_auto_set is False
    assert campaign.coordination_status == "measured_runtime_observation"
    assert payload["collective_intelligence"] is False
    earned = earn_collective_intelligence_candidate_flags(smoke=True)
    assert all(value is False for value in earned.as_mapping().values())
    assert evaluate_phase_k_claim(campaign).final_claim == "runtime_observation"
    _assert_forbidden(payload)
    assert (
        ScientificClaimGate()
        .decide(ClaimRequest("collective_intelligence_candidate", payload))
        .allowed
        is False
    )


def test_goldsby_harness_smoke_has_three_delays_and_research_default_50() -> None:
    assert GOLDSBY_RESEARCH_REPLICATE_COUNT == 50
    assert GOLDSBY_LITERATURE_DELAYS == (0, 25, 50)
    campaign = run_goldsby_cpu_delay_specialist_campaign(smoke=True)
    payload = campaign.to_dict()
    assert len(campaign.seeds) == GOLDSBY_SMOKE_REPLICATE_COUNT
    assert campaign.literature_delays == (0, 25, 50)
    assert len(campaign.treatments) == 3
    assert campaign.is_goldsby_2012_pnas_experiment is False
    assert campaign.major_transition_in_individuality is False
    assert campaign.claim_gate_flags_auto_set is False
    assert campaign.research_replicate_default == 50
    assert {item.literature_delay_cycles for item in campaign.treatments} == {0, 25, 50}
    assert all(
        item.replicate_count == GOLDSBY_SMOKE_REPLICATE_COUNT for item in campaign.treatments
    )
    _assert_forbidden(payload)
    with pytest.raises(ConfigurationError, match="must not claim"):
        campaign.__class__(
            seeds=(1, 2),
            generations=2,
            n_groups=2,
            group_size=4,
            literature_delays=(0, 50),
            treatments=campaign.treatments[:2],
            is_goldsby_2012_pnas_experiment=True,
        )


def test_isolation_hook_distinguishes_missing_work_instruction() -> None:
    specialist_a = (ISA_WORK_A, ISA_WORK_A, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP)
    specialist_b = (ISA_WORK_B, ISA_WORK_B, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP)
    record = measure_isolation_competence(
        (specialist_a, specialist_b, specialist_a, specialist_b),
        group_size=4,
        cpu_delay_cycles=0,
        ancestral_genomes=(
            (ISA_WORK_A, ISA_WORK_B, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP),
        )
        * 4,
    )
    assert record.isolation_dual_task_failed is True
    assert record.genomes_missing_complementary_work == 4
    assert record.instruction_loss_evolved is True
    assert record.isolation_collapse_is_evolved_autonomy_loss is False
    assert record.to_dict()["major_transition_in_individuality"] is False


def test_multi_generation_price_estimates_transmission_and_keeps_complete_false() -> None:
    campaign = run_multi_generation_price_analysis(smoke=True)
    payload = campaign.to_dict()
    assert campaign.transmission_term_estimated is True
    assert campaign.price_equation_complete is False
    assert campaign.major_transition_in_individuality is False
    assert campaign.price_equation_status == "measured_runtime_observation"
    assert campaign.claim_gate_flags_auto_set is False
    assert campaign.transmission_identity_holds is True
    step = campaign.seed_records[0].mls.steps[0]
    assert abs(step.residual) <= 1e-8
    assert campaign.seed_records[0].mls.last_generation_mls1["transmission_term_estimated"] is False
    _assert_forbidden(payload)
    with pytest.raises(ConfigurationError, match="at least two seeds"):
        run_multi_generation_price_analysis(seeds=(3,))


def test_conflict_suppression_hooks_stay_endogenous_false() -> None:
    observation = build_conflict_suppression_observation()
    payload = observation.to_dict()
    assert observation.conflict_suppression_measured is True
    assert observation.conflict_suppression_endogenous is False
    assert observation.germline_sequestration_endogenous is False
    assert observation.export_of_fitness_detected is False
    assert observation.major_transition_in_individuality is False
    assert observation.cheater.conflict_suppression_endogenous is False
    assert observation.revertant.entrenchment_of_multicellularity is False
    assert observation.revertant.isolation_collapse_is_payoff_construction is True
    assert payload["collective_intelligence"] is False
    _assert_forbidden(payload)
    cheater = run_cheater_invasion_assay((0.1, 0.9, 0.15, 0.85), seed=11)
    revertant = run_revertant_isolation_assay((0.1, 0.9, 0.15, 0.85), seed=11)
    assert cheater.suppression_mechanism == "group_replacement_bookkeeping"
    assert revertant.revertant_assay_status == "measured_runtime_observation"
    with pytest.raises(ConfigurationError, match="endogenous"):
        ConflictSuppressionObservation(
            mls_within_group_personal_variance=0.1,
            organism_within_group_personal_variance=0.2,
            conflict_index_mls=0.1,
            conflict_index_organism=0.2,
            variance_reduction_under_mls=0.5,
            cheater=cheater,
            revertant=revertant,
            conflict_suppression_endogenous=True,
        )


def test_phase_k_public_api_bindings() -> None:
    for name in (
        "run_evolved_coordination_instruction_experiment",
        "run_goldsby_cpu_delay_specialist_campaign",
        "run_multi_generation_price_analysis",
        "build_conflict_suppression_observation",
        "evaluate_coordination_group",
        "run_cheater_invasion_assay",
        "run_revertant_isolation_assay",
        "EvolvedCoordinationCampaign",
        "GoldsbyCpuDelayCampaign",
        "MultiGenerationPriceCampaign",
        "ConflictSuppressionObservation",
        "GOLDSBY_RESEARCH_REPLICATE_COUNT",
        "COORDINATION_ISA",
        "evaluate_phase_k_claim",
    ):
        assert hasattr(g, name)
        assert name in g.__all__
    assert set(COORDINATION_ISA) >= {ISA_SEND, ISA_RETRIEVE, ISA_BROADCAST, ISA_WORK_A, ISA_WORK_B}
    assert g.GOLDSBY_RESEARCH_REPLICATE_COUNT == 50
