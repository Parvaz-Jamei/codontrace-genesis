"""Phase L Avida messaging / DEME_GROUP / Goldsby-aligned measurements.

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
    earn_collective_intelligence_candidate_flags,
)
from codontrace.genesis.phase_k import (
    ISA_BROADCAST,
    ISA_NOP,
    ISA_RETRIEVE,
    ISA_SEND,
    ISA_WORK_A,
    ISA_WORK_B,
    EvolvedCoordinationCampaign,
    EvolvedCoordinationSeedRecord,
    run_evolved_coordination_instruction_experiment,
)
from codontrace.genesis.phase_l import (
    FIDELITY_ISA,
    ISA_BLOCK,
    ISA_ROTATE,
    CoordinationAblationEvidence,
    GoldsbyAlignedSpecialistRecord,
    evaluate_organism_messaging_group,
    evaluate_phase_l_claim,
    feed_phase_k_coordination_ablation_evidence,
    measure_goldsby_aligned_specialists,
    phase_k_coordination_to_communication_ablation,
    run_goldsby_aligned_specialist_campaign,
    run_organism_messaging_fidelity_experiment,
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


def _research_coordination_campaign(*, drop: float = 3.0) -> EvolvedCoordinationCampaign:
    records = tuple(
        EvolvedCoordinationSeedRecord(
            seed=11 + index,
            mean_group_fitness=8.0,
            ablated_group_fitness=8.0 - drop,
            ablation_drop=drop,
            coordination_payoff=4.0,
            send_frequency=0.2,
            retrieve_frequency=0.2,
            broadcast_frequency=0.1,
            successful_retrieve=3,
            evolved_not_assigned=True,
            coordination_pays=drop > 0.0,
            nmi=0.4,
        )
        for index in range(RESEARCH_SEED_COUNT)
    )
    return EvolvedCoordinationCampaign(
        seeds=tuple(11 + index for index in range(RESEARCH_SEED_COUNT)),
        generations=RESEARCH_GENERATION_COUNT,
        n_groups=8,
        group_size=4,
        seed_records=records,
        mean_ablation_drop=drop,
        mean_coordination_payoff=4.0,
        mean_send_frequency=0.2,
        mean_retrieve_frequency=0.2,
        claim_gate_flags_auto_set=False,
    )


def test_phase_a_life_loop_digest_pin_unchanged_by_phase_l() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST


def test_rag_corpus_includes_avida_cfg_and_wiki_cites() -> None:
    corpus = load_default_corpus()
    assert len(corpus) >= 18
    ids = {item.doc_id for item in corpus.documents()}
    assert "avida_cfg_organism_messaging" in ids
    assert "avida_cfg_deme_group" in ids
    assert "goldsby_2012_pnas_task_switching" in ids
    assert corpus.digest() == load_default_corpus().digest()
    messaging = search_corpus("Avida ORGANISM_MESSAGING send-msg retrieve-msg FIFO facing", k=6)
    assert any("organism_messaging" in hit.document.doc_id for hit in messaging.hits)
    demes = search_corpus("avida.cfg DEME_GROUP DEMES_GROUP_REPLICATE GERMLINE wiki", k=6)
    assert any("deme_group" in hit.document.doc_id for hit in demes.hits)


def test_facing_send_pops_fifo_and_block_stops_broadcast() -> None:
    sender = (ISA_WORK_A, ISA_SEND, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP)
    retriever = (ISA_NOP, ISA_NOP, ISA_RETRIEVE, ISA_WORK_B, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP)
    paid = evaluate_organism_messaging_group(
        (sender, retriever),
        messaging_enabled=True,
        organism_ids=("a", "b"),
        deme_id="pay",
    )
    ablated = evaluate_organism_messaging_group(
        (sender, retriever),
        messaging_enabled=False,
        organism_ids=("a", "b"),
        deme_id="off",
    )
    assert paid.uses_per_organism_fifo is True
    assert paid.uses_facing_neighbor_send is True
    assert paid.is_avida_cpp_port is False
    assert paid.analog_not_port is True
    assert paid.successful_retrieve >= 1
    assert paid.coordination_payoff > 0.0
    assert paid.group_fitness > ablated.group_fitness
    assert ablated.successful_retrieve == 0

    broadcaster = (ISA_WORK_A, ISA_BROADCAST, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP)
    blocked = (ISA_WORK_A, ISA_BLOCK, ISA_BROADCAST, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP)
    fanout = evaluate_organism_messaging_group((broadcaster, retriever), messaging_enabled=True)
    stopped = evaluate_organism_messaging_group((blocked, retriever), messaging_enabled=True)
    assert fanout.n_broadcast >= 1
    assert fanout.successful_retrieve >= 1
    assert stopped.n_block >= 1
    assert stopped.blocked_broadcasts >= 1
    assert stopped.successful_retrieve == 0
    _assert_forbidden(paid.to_dict())


def test_deme_group_analog_preserves_target_deme() -> None:
    workers = (
        (ISA_WORK_A, ISA_WORK_A, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP),
        (ISA_WORK_B, ISA_WORK_B, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP),
    )
    replicated = evaluate_organism_messaging_group(
        workers,
        messaging_enabled=False,
        deme_replicate_threshold=0.1,
        replicate_copy_germline=True,
        germline_member_index=0,
        deme_id="src",
    )
    silent = evaluate_organism_messaging_group(
        workers,
        messaging_enabled=False,
        deme_replicate_threshold=99.0,
        deme_id="quiet",
    )
    assert replicated.deme_replication_events
    assert replicated.extra_target_deme_preserved is True
    assert replicated.germline_parent_ids
    assert silent.deme_replication_events == ()
    assert silent.extra_target_deme_preserved is False
    assert replicated.is_avida_cpp_port is False


def test_messaging_fidelity_smoke_is_measured_and_does_not_earn() -> None:
    with pytest.raises(ConfigurationError, match="at least two seeds"):
        run_organism_messaging_fidelity_experiment(seeds=(3,))
    campaign = run_organism_messaging_fidelity_experiment(smoke=True)
    payload = campaign.to_dict()
    assert len(campaign.seeds) == SMOKE_SEED_COUNT
    assert campaign.generations == SMOKE_GENERATION_COUNT
    assert campaign.uses_per_organism_fifo is True
    assert campaign.uses_block_propagation is True
    assert campaign.uses_deme_group_analog is True
    assert campaign.is_avida_cpp_port is False
    assert campaign.claim_gate_flags_auto_set is False
    assert campaign.messaging_status == "measured_runtime_observation"
    assert payload["collective_intelligence"] is False
    assert evaluate_phase_l_claim(campaign).final_claim == "runtime_observation"
    _assert_forbidden(payload)
    assert (
        ScientificClaimGate()
        .decide(ClaimRequest("collective_intelligence_candidate", payload))
        .allowed
        is False
    )


def test_goldsby_aligned_specialists_stay_not_pnas() -> None:
    specialist_a = (ISA_WORK_A, ISA_WORK_A, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP)
    specialist_b = (ISA_WORK_B, ISA_WORK_B, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP)
    record = measure_goldsby_aligned_specialists(
        (specialist_a, specialist_b, specialist_a, specialist_b),
        group_size=4,
        cpu_delay_cycles=0,
        ancestral_genomes=(
            (ISA_WORK_A, ISA_WORK_B, ISA_NOP, ISA_NOP, ISA_NOP, ISA_NOP),
        )
        * 4,
    )
    assert record.genotypic_specialist_fraction == 1.0
    assert record.behavioral_specialist_fraction == 1.0
    assert record.colony_quota_is_analog is True
    assert record.clonal_genomes_identical is True
    assert record.is_goldsby_2012_pnas_experiment is False
    assert record.isolation_collapse_is_evolved_autonomy_loss is False
    assert record.uses_avida_hardware is False
    assert record.instruction_loss_evolved is True
    with pytest.raises(ConfigurationError, match="must not claim"):
        GoldsbyAlignedSpecialistRecord(
            literature_delay_cycles=50,
            analog_switch_cpu_cost=4,
            genotypic_specialist_fraction=0.5,
            behavioral_specialist_fraction=0.5,
            generalist_residual_fraction=0.1,
            gorelick_nmi=0.2,
            colony_quota_a=1.0,
            colony_quota_b=1.0,
            colony_quota_met=False,
            colony_quota_is_analog=True,
            clonal_behavioral_nmi=0.1,
            clonal_behavioral_specialist_fraction=0.2,
            clonal_genomes_identical=True,
            ancestral_isolation_competence=1.0,
            evolved_isolation_competence=0.0,
            isolation_competence_delta=-1.0,
            isolation_dual_task_failed=True,
            genomes_missing_complementary_work=4,
            instruction_loss_evolved=True,
            isolation_collapse_is_cpu_delay=False,
            isolation_collapse_is_payoff_construction=False,
            isolation_collapse_is_evolved_autonomy_loss=False,
            is_goldsby_2012_pnas_experiment=True,
            uses_avida_hardware=False,
            uses_clonal_groups=True,
        )


def test_goldsby_aligned_campaign_smoke() -> None:
    campaign = run_goldsby_aligned_specialist_campaign(smoke=True, delays=(0, 50))
    payload = campaign.to_dict()
    assert len(campaign.seeds) == 4
    assert campaign.literature_delays == (0, 50)
    assert len(campaign.treatments) == 2
    assert campaign.is_goldsby_2012_pnas_experiment is False
    assert campaign.claim_gate_flags_auto_set is False
    assert campaign.dose_response.is_goldsby_2012_pnas_experiment is False
    assert campaign.research_replicate_default == 50
    _assert_forbidden(payload)


def test_phase_k_ablation_feed_does_not_auto_set_flags() -> None:
    smoke_campaign = run_evolved_coordination_instruction_experiment(smoke=True)
    packaged = feed_phase_k_coordination_ablation_evidence(smoke_campaign)
    assert packaged.claim_gate_flags_auto_set is False
    assert packaged.claim_gate_ablation_result_set is False
    assert packaged.propose_candidate_flags is False
    assert all(value is False for value in packaged.as_mapping().values())
    adapted = phase_k_coordination_to_communication_ablation(smoke_campaign)
    assert adapted.claim_gate_ablation_result_set is False
    earned_smoke = earn_collective_intelligence_candidate_flags(
        coordination=smoke_campaign, smoke=True
    )
    assert earned_smoke.as_mapping()["ablation_result"] is False
    research = _research_coordination_campaign()
    default_feed = feed_phase_k_coordination_ablation_evidence(research)
    assert default_feed.as_mapping()["ablation_result"] is False
    proposed = feed_phase_k_coordination_ablation_evidence(
        research, propose_candidate_flags=True, smoke=False
    )
    flags = proposed.as_mapping()
    assert flags["ablation_result"] is True
    assert flags["replay_verification"] is False
    assert flags["heldout_protocol"] is False
    assert proposed.claim_gate_flags_auto_set is False
    gate = ScientificClaimGate()
    assert gate.decide(ClaimRequest("collective_intelligence", flags)).allowed is False
    assert gate.decide(ClaimRequest("collective_intelligence_candidate", flags)).allowed is False
    no_drop = _research_coordination_campaign(drop=0.0)
    unpaid = feed_phase_k_coordination_ablation_evidence(
        no_drop, propose_candidate_flags=True, smoke=False
    )
    assert unpaid.as_mapping()["ablation_result"] is False
    with pytest.raises(ConfigurationError, match="must not auto-set"):
        CoordinationAblationEvidence(
            source_schema="x",
            source_digest="d",
            seeds=(1, 2),
            generations=20,
            mean_ablation_drop=1.0,
            successful_retrieve_total=1,
            coordination_pays=True,
            uses_phase_e_messaging=True,
            proposed_flags=earned_smoke,
            propose_candidate_flags=False,
            claim_gate_flags_auto_set=True,
        )


def test_phase_l_public_api_bindings() -> None:
    for name in (
        "evaluate_organism_messaging_group",
        "run_organism_messaging_fidelity_experiment",
        "run_goldsby_aligned_specialist_campaign",
        "measure_goldsby_aligned_specialists",
        "feed_phase_k_coordination_ablation_evidence",
        "phase_k_coordination_to_communication_ablation",
        "OrganismMessagingFidelityCampaign",
        "GoldsbyAlignedSpecialistCampaign",
        "CoordinationAblationEvidence",
        "CoordinationAblationLike",
        "FIDELITY_ISA",
        "evaluate_phase_l_claim",
    ):
        assert hasattr(g, name)
        assert name in g.__all__
    assert set(FIDELITY_ISA) >= {
        ISA_SEND,
        ISA_RETRIEVE,
        ISA_BROADCAST,
        ISA_BLOCK,
        ISA_ROTATE,
        ISA_WORK_A,
        ISA_WORK_B,
    }
