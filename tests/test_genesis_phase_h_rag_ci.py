"""Phase H literature RAG + collective-intelligence pathway (measurement-first).

These tests document software capability. They do not claim intelligence,
collective intelligence, Tokyo Type 1 passed, or Avida replacement.
"""

from __future__ import annotations

import pytest

import codontrace.genesis as g
from codontrace.errors import ConfigurationError
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.phase_h import (
    RESEARCH_SEED_COUNT,
    SMOKE_SEED_COUNT,
    TaskSwitchingCostConfig,
    apply_task_switching_cost_to_dol,
    collective_intelligence_candidate_checklist,
    count_task_switches,
    evaluate_phase_h_claim,
    format_collective_intelligence_candidate_checklist,
    run_communication_ablation_experiment,
    run_group_vs_individual_effect_size_campaign,
)
from codontrace.genesis.rag import (
    ResearchDocument,
    cite_sources,
    ingest_document,
    load_default_corpus,
    search_corpus,
)
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

LIFE_LOOP_SPEC_DIGEST = "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"


def test_phase_a_life_loop_digest_pin_unchanged_by_phase_h() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert spec.digest() == LIFE_LOOP_SPEC_DIGEST


def test_default_rag_corpus_is_nonempty_and_digest_stable() -> None:
    corpus = load_default_corpus()
    assert len(corpus) >= 11
    ids = {item.doc_id for item in corpus.documents()}
    assert "goldsby_2012_pnas_task_switching" in ids
    assert "channon_2024_tokyo_type1" in ids
    assert "goldsby_ofria_avida_messaging_germline" in ids
    assert "miikkulainen_forrest_2021_nature_mi" in ids
    assert "cao_yang_2026_vocabulary_verifier_gaps" in ids
    assert "chaturvedi_2026_role_mls" in ids
    assert "conlin_2023_dol_multicellularity_avida" in ids
    assert corpus.digest() == load_default_corpus().digest()
    assert len(corpus.digest()) == 64
    for document in corpus.documents():
        assert document.codontrace_has
        assert document.codontrace_lacks
        assert document.next_experiment
        assert document.claim_ceiling


def test_search_returns_goldsby_and_channon_for_obvious_queries() -> None:
    goldsby = search_corpus("Goldsby task switching costs division of labor PNAS Avida", k=5)
    goldsby_ids = [hit.document.doc_id for hit in goldsby.hits]
    assert any("goldsby" in doc_id for doc_id in goldsby_ids)
    channon = search_corpus("Channon 2024 Tokyo Type 1 procedure measurement not a pass", k=5)
    channon_ids = [hit.document.doc_id for hit in channon.hits]
    assert any("channon" in doc_id for doc_id in channon_ids)
    cites = cite_sources(goldsby)
    assert cites == goldsby.citations()
    assert any("Goldsby" in line for line in cites)


def test_collective_intelligence_query_ranks_literature_gaps() -> None:
    result = search_corpus("how to get collective intelligence evidence", k=8)
    ids = [hit.document.doc_id for hit in result.hits]
    assert any("goldsby" in doc_id for doc_id in ids)
    assert result.to_dict()["collective_intelligence"] is False
    assert result.to_dict()["intelligence"] is False
    assert result.digest == search_corpus("how to get collective intelligence evidence", k=8).digest


def test_ingest_document_is_public_and_searchable() -> None:
    corpus = load_default_corpus()
    extra = ResearchDocument(
        doc_id="phase_h_test_note",
        title="CodonTrace Genesis Phase H test ingest",
        authors=("CodonTrace Genesis",),
        year=2026,
        venue="test fixture",
        tags=("ingest", "phase-h"),
        summary="Fixture document used to test ingest_document.",
        codontrace_has="retriever ingest API",
        codontrace_lacks="not a paper",
        next_experiment="delete after test",
    )
    ingest_document(extra, corpus)
    hit = corpus.search("Phase H test ingest fixture", k=1)
    assert hit.hits[0].document.doc_id == "phase_h_test_note"


def test_claimgate_still_blocks_intelligence_and_collective_intelligence() -> None:
    gate = ScientificClaimGate()
    payload = search_corpus("collective intelligence Goldsby messaging", k=3).to_dict()
    for label in (
        "collective_intelligence",
        "proved_collective_intelligence",
        "intelligence",
        "agi",
        "tokyo_type1_passed",
        "open_ended_intelligence",
        "avida_replacement",
    ):
        decision = gate.decide(ClaimRequest(label, payload))
        assert decision.allowed is False
    candidate = gate.decide(ClaimRequest("collective_intelligence_candidate", payload))
    assert candidate.allowed is False


def test_collective_intelligence_candidate_checklist_lists_missing_flags() -> None:
    empty = collective_intelligence_candidate_checklist()
    assert empty.auto_set_flags is False
    assert empty.claim_allowed is False
    assert set(empty.missing_flags) == set(empty.required_flags)
    assert "ablation_result" in empty.missing_flags
    assert "heldout_protocol" in empty.missing_flags
    text = format_collective_intelligence_candidate_checklist()
    assert "does not set flags" in text
    assert "MISSING  ablation_result" in text
    partial = collective_intelligence_candidate_checklist(
        {"real_partner_event": True, "replay_verification": True}
    )
    assert "real_partner_event" in partial.present_flags
    assert "ablation_result" in partial.missing_flags
    assert partial.claim_allowed is False
    still_blocked = ScientificClaimGate().decide(
        ClaimRequest("collective_intelligence", {"ablation_result": True})
    )
    assert still_blocked.allowed is False


def test_task_switching_cost_hook_reweights_dol_metrics() -> None:
    assert count_task_switches(("EAT_LUMEN", "EAT_LUMEN", "WAIT", "EAT_LUMEN")) == 2
    spec = GenesisRuntimeProfile.phase_e_substrate_world(
        seed=7, tick_count=4, population=4, enable_demes=True, enable_roles=True
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    zero = apply_task_switching_cost_to_dol(result, config=TaskSwitchingCostConfig(cost=0.0))
    assert zero
    for row in zero:
        assert row.cost == 0.0
        assert row.fitness_share_changed is False
        assert 0.0 <= row.specialization_index <= 1.0
        assert row.to_dict()["evolved_division_of_labor"] is False
        assert row.to_dict()["collective_intelligence"] is False
    high = apply_task_switching_cost_to_dol(result, cost=10.0)
    assert len(high) == len(zero)
    assert high[0].cost == 10.0
    if any(row.switch_count_total > 0 for row in high):
        assert any(row.cost == 10.0 for row in high)


def test_communication_ablation_harness_is_runnable_and_honest() -> None:
    campaign = run_communication_ablation_experiment(seeds=(3, 7), tick_count=4, population=4)
    payload = campaign.to_dict()
    assert len(campaign.seeds) == SMOKE_SEED_COUNT
    assert campaign.communication_ablation_status == "measured_runtime_observation"
    assert campaign.claim_gate_ablation_result_set is False
    assert payload["collective_intelligence"] is False
    assert evaluate_phase_h_claim(campaign).final_claim == "runtime_observation"
    assert (
        ScientificClaimGate()
        .decide(ClaimRequest("collective_intelligence_candidate", payload))
        .allowed
        is False
    )
    for record in campaign.seed_records:
        assert record.messages_on >= 0
        assert record.messages_off >= 0


def test_group_vs_individual_effect_size_fields_and_seed_count() -> None:
    with pytest.raises(ConfigurationError, match="at least two seeds"):
        run_group_vs_individual_effect_size_campaign(seeds=(3,))
    pack = run_group_vs_individual_effect_size_campaign(seed_count=2, tick_count=4, population=4)
    payload = pack.to_dict()
    assert pack.seed_count == 2
    assert pack.research_default_seed_count == RESEARCH_SEED_COUNT
    assert "mean_delta" in payload
    assert "cohens_d" in payload
    assert "effect_size_status" in payload
    assert payload["heldout_partner_status"] == "not_run"
    assert payload["communication_ablation_status"] == "not_run"
    assert payload["collective_intelligence"] is False
    assert payload["major_transition_in_individuality"] is False
    assert evaluate_phase_h_claim(pack).allowed is True
    assert (
        ScientificClaimGate().decide(ClaimRequest("collective_intelligence", payload)).allowed
        is False
    )


def test_phase_h_public_api_bindings() -> None:
    for name in (
        "search_corpus",
        "load_default_corpus",
        "cite_sources",
        "ingest_document",
        "run_communication_ablation_experiment",
        "run_group_vs_individual_effect_size_campaign",
        "apply_task_switching_cost_to_dol",
        "collective_intelligence_candidate_checklist",
        "print_collective_intelligence_candidate_checklist",
        "GroupVsIndividualEffectSize",
        "CommunicationAblationCampaign",
        "TaskSwitchingCostConfig",
    ):
        assert hasattr(g, name)
        assert name in g.__all__
