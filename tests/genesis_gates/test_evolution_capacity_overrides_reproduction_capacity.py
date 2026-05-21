from __future__ import annotations

from dataclasses import replace

from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.population import GenerationResult
from codontrace.genesis.selection import EvolutionConfig


def test_evolution_capacity_overrides_reproduction_capacity_and_is_audited() -> None:
    spec = GenesisExperimentSpec(
        genome_bits=("000", "000", "000"),
        tick_count=1,
        population_max=10,
        evolution_config=EvolutionConfig(max_population=2, selection_policy="fitness_proportional"),
        initial_runtime_atp=10.0,
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    generation = result.ticks[0].generation_result

    assert generation.before_count == 3
    assert generation.after_count == 2
    assert generation.selection_result is not None
    assert generation.selection_result.before_count == 3
    assert generation.selection_result.after_count == 2
    assert len(generation.selection_result.dropped_ids) == 1

    restored = GenerationResult.from_dict(generation.to_dict())
    assert restored.selection_result is not None
    assert restored.selection_result.to_dict() == generation.selection_result.to_dict()

    changed = replace(
        generation,
        selection_result=replace(generation.selection_result, dropped_ids=("different",)),
    )
    assert changed.digest() != generation.digest()
