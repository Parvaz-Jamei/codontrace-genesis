"""Regression tests for codontrace==0.3.0b2 eval bugs.

These tests document software capability and runtime observation only. They do
not claim intelligence, instinct evolution, OEE, Tokyo Type 1 passed, or that
CodonTrace replaces Avida.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.birth import ReproductionMode, coerce_reproduction_mode
from codontrace.genesis.claim_gate import (
    TOKYO_TYPE1_MEASUREMENT_CLAIM,
    ClaimRequest,
    ScientificClaimGate,
)
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.environment import summarize_dynamic_environment_observation
from codontrace.genesis.multi_generation import (
    build_multi_generation_evidence_pack,
    evaluate_tokyo_type1_measurement_claim,
)
from codontrace.genesis.phase_e import build_phase_e_evidence_pack, summarize_phase_e_observation
from codontrace.genesis.population import ReproductionConfig
from codontrace.genesis.runtime_profiles import (
    GenesisRuntimeProfile,
    summarize_life_loop_observation,
)


def test_sexual_birth_placement_metrics_count_chamber_offspring() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(
        seed=7,
        tick_count=12,
        population=6,
        reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER,
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    observation = summarize_life_loop_observation(result)
    assert observation.births > 0
    assert observation.heritable_sexual_pairs > 0
    assert observation.two_parent_lineage_records > 0
    placed = observation.adjacent_or_displaced_births + observation.same_cell_births
    assert placed >= observation.births
    assert placed > 0
    assert observation.claim_ceiling == "runtime_observation"
    chamber_records = [
        item
        for tick in result.ticks
        for item in tick.generation_result.birth_placement_records
    ]
    assert len(chamber_records) >= observation.births


def test_reproduction_mode_rejects_invalid_string() -> None:
    with pytest.raises((ValueError, ConfigurationError), match="Unsupported reproduction_mode"):
        ReproductionConfig(reproduction_mode="not_a_mode")
    with pytest.raises(ValueError, match="Unsupported reproduction_mode"):
        GenesisRuntimeProfile.life_loop_world(reproduction_mode="not_a_mode")
    with pytest.raises(TypeError, match="reproduction_mode must be"):
        coerce_reproduction_mode(123)  # type: ignore[arg-type]
    assert coerce_reproduction_mode("sexual_crossover") is ReproductionMode.SEXUAL_CROSSOVER
    assert coerce_reproduction_mode("asexual") is ReproductionMode.ASEXUAL
    spec = GenesisRuntimeProfile.life_loop_world(reproduction_mode="asexual")
    assert spec.population_configs is not None
    assert spec.population_configs.reproduction.reproduction_mode is ReproductionMode.ASEXUAL


def test_phase_e_capsule_memory_has_write_read_substitution_and_ablation_differs() -> None:
    on_spec = GenesisRuntimeProfile.phase_e_substrate_world(
        seed=7, tick_count=8, population=6, enable_capsule_memory=True, enable_demes=True
    )
    off_spec = GenesisRuntimeProfile.phase_e_substrate_world(
        seed=7,
        tick_count=8,
        population=6,
        enable_capsule_memory=False,
        enable_demes=True,
        seed_preferred_action="",
    )
    on_result = GenesisEngine.from_spec(on_spec).run_ticks()
    off_result = GenesisEngine.from_spec(off_spec).run_ticks()
    on_pack = build_phase_e_evidence_pack(on_result)
    off_pack = build_phase_e_evidence_pack(off_result)
    assert on_result.digest() != off_result.digest()
    assert on_pack.observation.capsule_writes > 0
    assert on_pack.observation.capsule_reads > 0
    assert on_pack.observation.capsule_substitutions > 0
    assert off_pack.observation.capsule_substitutions == 0
    assert off_pack.observation.capsule_reads == 0
    assert on_pack.observation.messages_sent > 0 or on_pack.observation.messages_retrieved > 0
    assert on_pack.claim_ceiling == "runtime_observation"
    assert on_pack.to_dict()["collective_intelligence_proved"] is False
    blocked = ScientificClaimGate().decide(ClaimRequest("collective_intelligence", {}))
    assert blocked.allowed is False


def test_life_loop_pop_equals_eight_can_birth() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=8)
    assert spec.population_max > 8
    assert spec.population_configs is not None
    assert spec.population_configs.reproduction.max_population > 8
    result = GenesisEngine.from_spec(spec).run_ticks()
    observation = summarize_life_loop_observation(result)
    assert observation.births > 0
    default = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=12, population=6)
    assert default.digest() == "7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac"
    assert default.population_max == 8


def test_summarize_helpers_reject_garbage_input() -> None:
    with pytest.raises(TypeError, match="run result"):
        summarize_life_loop_observation(None)
    with pytest.raises(TypeError, match="ticks collection"):
        summarize_life_loop_observation("not-a-result")
    with pytest.raises(TypeError, match="run result"):
        summarize_phase_e_observation(None)
    with pytest.raises(TypeError, match="ticks collection"):
        summarize_phase_e_observation(object())
    with pytest.raises(TypeError, match="run result"):
        summarize_dynamic_environment_observation(None)


def test_offspring_placement_rejects_invalid_string() -> None:
    with pytest.raises(ConfigurationError, match="Unsupported offspring_placement"):
        ReproductionConfig(offspring_placement="not_a_policy")  # type: ignore[arg-type]


def test_scientific_authorities_2026_doc_maps_each_fix() -> None:
    path = Path("docs/SCIENTIFIC_AUTHORITIES_2026.md")
    text = path.read_text(encoding="utf-8")
    for needle in (
        "sexual_birth_placement_metrics",
        "reproduction_mode_validation",
        "phase_e_capsule_wiring",
        "life_loop_capacity_footgun",
        "summarize_garbage_input",
        "tokyo_type1_measurement_hook",
        "Dolson",
        "Channon 2024",
        "tokyo_type1_measurement_only",
        "Ofria & Wilke 2004",
        "VERSION_ID",
        "2.14.0",
        "POPULATION_CAP",
        "PREFER_EMPTY",
        "RECOMBINATION_GROUP",
        "Clune 2007",
        "Ghalambor",
        "JaxLife",
        "Aevol_4b",
        "OntoAvida",
        "2412.17799",
        "CLIP",
        "Type 1 not passed",
        "BMC Evol Biol 2021",
        "Logic-9",
        "build_empirical_systematics_shadow",
        "TWO_FOLD_COST_SEX",
    ):
        assert needle in text, needle


def test_tokyo_type1_measurement_only_aliases_and_type1_passed_is_forbidden() -> None:
    gate = ScientificClaimGate()
    assert TOKYO_TYPE1_MEASUREMENT_CLAIM == "tokyo_type1_measurement_only"
    mapped = gate.decide(
        ClaimRequest(TOKYO_TYPE1_MEASUREMENT_CLAIM, {"oee_metrics": True})
    )
    assert mapped.allowed is True
    assert mapped.final_claim == "oee_measurement_only"
    for label in (
        "tokyo_type1_passed",
        "tokyo_type_1_passed",
        "tokyo_type1_oee_proved",
        "open_ended_intelligence",
    ):
        blocked = gate.decide(ClaimRequest(label, {"oee_metrics": True}))
        assert blocked.allowed is False
        assert blocked.decision == "rejected_overclaim_alias"


def test_evaluate_tokyo_type1_measurement_claim_never_says_type1_passed() -> None:
    spec = GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=8, population=6)
    result = GenesisEngine.from_spec(spec).run_ticks()
    pack = build_multi_generation_evidence_pack(result, spec=spec)
    decision = evaluate_tokyo_type1_measurement_claim(pack)
    assert decision.requested_claim == TOKYO_TYPE1_MEASUREMENT_CLAIM
    assert decision.final_claim == "oee_measurement_only"
    assert decision.final_claim != "tokyo_type1_passed"
    assert "passed" not in decision.final_claim
    import codontrace.genesis as g

    assert "evaluate_tokyo_type1_measurement_claim" in g.__all__
    assert "TOKYO_TYPE1_MEASUREMENT_CLAIM" in g.__all__
