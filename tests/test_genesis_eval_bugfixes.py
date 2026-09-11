"""Regression tests for codontrace==0.3.0b2 eval bugs.

These tests document software capability and runtime observation only. They do
not claim intelligence, instinct evolution, OEE, or that CodonTrace replaces
Avida.
"""

from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.birth import ReproductionMode, coerce_reproduction_mode
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine
from codontrace.genesis.environment import summarize_dynamic_environment_observation
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
