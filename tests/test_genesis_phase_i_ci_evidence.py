"""Phase I collective-intelligence evidence harnesses (measurement-first).

These tests document software capability. They do not claim intelligence,
collective intelligence, Tokyo Type 1 passed, or Avida replacement.
"""

from __future__ import annotations

import pytest

import codontrace.genesis as g
from codontrace.errors import ConfigurationError
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.phase_i import (
    EARNABLE_FLAG_SOURCES,
    RESEARCH_GENERATION_COUNT,
    RESEARCH_SEED_COUNT,
    SMOKE_GENERATION_COUNT,
    SMOKE_SEED_COUNT,
    build_export_of_fitness_observation,
    earn_collective_intelligence_candidate_flags,
    evaluate_phase_i_claim,
    gorelick_normalized_mutual_information,
    phase_i_candidate_checklist,
    run_evolved_division_of_labor_experiment,
    run_heldout_unfamiliar_partner_experiment,
    run_mls_evolutionary_outcome_experiment,
)
from codontrace.genesis.rag import load_default_corpus, search_corpus
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

LIFE_LOOP_SPEC_DIGEST = "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"


def test_phase_a_life_loop_digest_pin_unchanged_by_phase_i() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST


def test_rag_corpus_includes_phase_i_cites() -> None:
    corpus = load_default_corpus()
    assert len(corpus) >= 14
    ids = {item.doc_id for item in corpus.documents()}
    assert "gorelick_2004_normalized_mutual_entropy_dol" in ids
    assert "okasha_2006_levels_of_selection" in ids
    assert "michod_2007_pnas_export_of_fitness" in ids
    assert corpus.digest() == load_default_corpus().digest()
    gorelick = search_corpus("Gorelick normalized mutual information division of labor", k=5)
    assert any("gorelick" in hit.document.doc_id for hit in gorelick.hits)
    okasha = search_corpus("Okasha MLS2 evolutionary outcome levels of selection", k=5)
    assert any("okasha" in hit.document.doc_id for hit in okasha.hits)
    michod = search_corpus("Michod export of fitness conflict suppression individuality", k=5)
    assert any("michod" in hit.document.doc_id for hit in michod.hits)


def test_gorelick_nmi_needs_repeated_observations() -> None:
    specialists = gorelick_normalized_mutual_information(
        (("a", "A"), ("a", "A"), ("b", "B"), ("b", "B"))
    )
    generalists = gorelick_normalized_mutual_information(
        (("a", "A"), ("a", "B"), ("b", "A"), ("b", "B"))
    )
    assert specialists == 1.0
    assert generalists == 0.0


def test_heldout_unfamiliar_partner_smoke_is_measured_and_does_not_earn_flags() -> None:
    with pytest.raises(ConfigurationError, match="at least two seeds"):
        run_heldout_unfamiliar_partner_experiment(seeds=(3,))
    campaign = run_heldout_unfamiliar_partner_experiment(smoke=True)
    payload = campaign.to_dict()
    assert len(campaign.seeds) == SMOKE_SEED_COUNT
    assert campaign.generations == SMOKE_GENERATION_COUNT
    assert campaign.heldout_partner_status == "measured_runtime_observation"
    assert campaign.claim_gate_flags_auto_set is False
    assert payload["collective_intelligence"] is False
    assert all(row.distinct_partners for row in campaign.seed_records)
    assert all(row.leakage_status == "clean" for row in campaign.seed_records)
    earned = earn_collective_intelligence_candidate_flags(heldout=campaign, smoke=True)
    assert earned.auto_set is False
    assert all(value is False for value in earned.as_mapping().values())
    assert evaluate_phase_i_claim(campaign).final_claim == "runtime_observation"
    assert (
        ScientificClaimGate()
        .decide(ClaimRequest("collective_intelligence_candidate", payload))
        .allowed
        is False
    )


def test_evolved_division_of_labor_is_not_assigned_and_ablation_can_pay() -> None:
    campaign = run_evolved_division_of_labor_experiment(smoke=True)
    payload = campaign.to_dict()
    assert campaign.evolved_not_assigned is True
    assert campaign.claim_gate_ablation_result_set is False
    assert campaign.claim_gate_flags_auto_set is False
    assert payload["collective_intelligence"] is False
    assert campaign.mean_ablation_drop > 0.0
    assert any(row.evolved_division_of_labor_pays for row in campaign.seed_records)
    for row in campaign.seed_records:
        assert row.assigned_roles is False
        assert row.strategy == "mixed_specialists"
    earned = earn_collective_intelligence_candidate_flags(evolved_dol=campaign, smoke=True)
    assert earned.as_mapping()["role_complementarity"] is False
    assert earned.as_mapping()["ablation_result"] is False


def test_mls_changes_evolutionary_outcome_vs_organism_only() -> None:
    campaign = run_mls_evolutionary_outcome_experiment(smoke=True)
    payload = campaign.to_dict()
    assert campaign.multilevel_selection_experiment == "measured_runtime_observation"
    assert campaign.major_transition_in_individuality is False
    assert campaign.claim_gate_flags_auto_set is False
    assert payload["collective_intelligence"] is False
    assert campaign.outcome_changed_fraction > 0.0
    assert any(row.outcome_changed for row in campaign.seed_records)
    assert any(row.mls_strategy == "mixed_specialists" for row in campaign.seed_records)
    assert any(row.organism_strategy == "a_specialist_monoculture" for row in campaign.seed_records)


def test_export_of_fitness_scaffold_keeps_major_transition_false() -> None:
    mls = run_mls_evolutionary_outcome_experiment(smoke=True)
    observation = build_export_of_fitness_observation(mls)
    payload = observation.to_dict()
    assert observation.major_transition_in_individuality is False
    assert observation.export_of_fitness_detected is False
    assert observation.conflict_suppression_endogenous is False
    assert observation.germline_sequestration_endogenous is False
    assert observation.isolation_collapse_is_payoff_construction is True
    assert payload["collective_intelligence"] is False
    with pytest.raises(ConfigurationError, match="cannot be True"):
        observation.__class__(
            mls=None,
            between_group_fitness_mean=1.0,
            within_group_personal_mean=1.0,
            isolation_competence=0.0,
            group_competence=1.0,
            isolation_collapse_ratio=0.0,
            isolation_collapse_is_payoff_construction=True,
            conflict_suppression_endogenous=False,
            germline_sequestration_endogenous=False,
            export_of_fitness_detected=False,
            major_transition_in_individuality=True,
        )


def test_research_scale_can_earn_candidate_flags_but_not_ci_or_replay() -> None:
    heldout = run_heldout_unfamiliar_partner_experiment(
        seed_count=RESEARCH_SEED_COUNT,
        generations=RESEARCH_GENERATION_COUNT,
        smoke=False,
    )
    dol = run_evolved_division_of_labor_experiment(
        seed_count=RESEARCH_SEED_COUNT,
        generations=RESEARCH_GENERATION_COUNT,
        smoke=False,
    )
    mls = run_mls_evolutionary_outcome_experiment(
        seed_count=RESEARCH_SEED_COUNT,
        generations=RESEARCH_GENERATION_COUNT,
        smoke=False,
    )
    earned = earn_collective_intelligence_candidate_flags(
        heldout=heldout, evolved_dol=dol, mls=mls, smoke=False
    )
    flags = earned.as_mapping()
    assert earned.research_scale is True
    assert flags["heldout_protocol"] is True
    assert flags["familiar_partner_protocol"] is True
    assert flags["unfamiliar_partner_protocol"] is True
    assert flags["real_partner_event"] is True
    assert flags["role_complementarity"] is True
    assert flags["collective_coordination"] is True
    assert flags["non_capsule_cooperation"] is True
    assert flags["ablation_result"] is True
    assert flags["collective_report_digest"] is True
    assert flags["replay_verification"] is False
    gate = ScientificClaimGate()
    assert gate.decide(ClaimRequest("collective_intelligence", flags)).allowed is False
    assert gate.decide(ClaimRequest("intelligence", flags)).allowed is False
    assert gate.decide(ClaimRequest("agi", flags)).allowed is False
    candidate = gate.decide(ClaimRequest("collective_intelligence_candidate", flags))
    assert candidate.allowed is False
    assert "missing_replay_verification" in candidate.failed_reasons
    checklist = phase_i_candidate_checklist(heldout=heldout, evolved_dol=dol, mls=mls, smoke=False)
    assert checklist.claim_allowed is False
    assert "replay_verification" in checklist.missing_flags
    assert "heldout_protocol" in checklist.present_flags
    assert "ablation_result" in checklist.present_flags


def test_checklist_documents_earnable_flag_sources() -> None:
    names = {item[0] for item in EARNABLE_FLAG_SOURCES}
    assert names == {
        "heldout_protocol",
        "familiar_partner_protocol",
        "unfamiliar_partner_protocol",
        "real_partner_event",
        "role_complementarity",
        "collective_coordination",
        "non_capsule_cooperation",
        "ablation_result",
        "collective_report_digest",
        "replay_verification",
    }
    replay = dict(EARNABLE_FLAG_SOURCES)["replay_verification"]
    assert "Not earnable from Phase I" in replay


def test_phase_i_public_api_bindings() -> None:
    for name in (
        "run_heldout_unfamiliar_partner_experiment",
        "run_evolved_division_of_labor_experiment",
        "run_mls_evolutionary_outcome_experiment",
        "build_export_of_fitness_observation",
        "earn_collective_intelligence_candidate_flags",
        "gorelick_normalized_mutual_information",
        "phase_i_candidate_checklist",
        "HeldoutUnfamiliarPartnerCampaign",
        "EvolvedDivisionOfLaborCampaign",
        "MlsEvolutionaryOutcomeCampaign",
        "ExportOfFitnessObservation",
        "EarnedCandidateFlags",
    ):
        assert hasattr(g, name)
        assert name in g.__all__
