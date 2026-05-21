from __future__ import annotations

from codontrace.genesis import (
    GenesisOrganism,
    MutationConfig,
    PopulationConfigs,
    PopulationRunner,
    PopulationState,
    ReproductionConfig,
    step_population,
)
from codontrace.world import World2D


def test_population_stigmergy_disabled_keeps_no_layer_and_zero_metrics() -> None:
    organism = GenesisOrganism.from_bits("a", "110", initial_runtime_atp=5.0, position=(1, 1))
    population = PopulationState(0, 0, (organism,), (), ())
    configs = PopulationConfigs(
        reproduction=ReproductionConfig(enabled=False),
        mutation=MutationConfig(bit_flip_rate=0.0),
        enable_nexus_stigmergy=False,
    )

    result = step_population(population, World2D(3, 3), configs)

    assert result.nexus_layer is None
    assert result.organism_records[0].capsule_emit_count == 0
    assert result.organism_records[0].capsule_read_count == 0


def test_population_stigmergy_emits_and_nearby_organism_reads() -> None:
    emitter = GenesisOrganism.from_bits("a", "110", initial_runtime_atp=5.0, position=(1, 1))
    reader = GenesisOrganism.from_bits("b", "000", initial_runtime_atp=5.0, position=(2, 1))
    population = PopulationState(0, 0, (reader, emitter), (), ())
    configs = PopulationConfigs(
        reproduction=ReproductionConfig(enabled=False),
        mutation=MutationConfig(bit_flip_rate=0.0),
        enable_nexus_stigmergy=True,
    )

    result = step_population(population, World2D(4, 4), configs)
    records = {record.organism_id: record for record in result.organism_records}

    assert result.nexus_layer is not None
    assert len(result.nexus_layer.signals) == 1
    assert records["a"].capsule_emit_count == 1
    assert records["b"].capsule_read_count == 1
    assert records["b"].nexus_signal_count_before == 1


def test_population_runner_retains_nexus_layer_after_generation() -> None:
    organism = GenesisOrganism.from_bits("a", "110", initial_runtime_atp=5.0, position=(1, 1))
    runner = PopulationRunner(
        PopulationState(0, 0, (organism,), (), ()),
        World2D(3, 3),
        PopulationConfigs(
            reproduction=ReproductionConfig(enabled=False),
            mutation=MutationConfig(bit_flip_rate=0.0),
            enable_nexus_stigmergy=True,
        ),
    )

    result = runner.step_generation(seed=1)

    assert result.nexus_layer is not None
    assert runner.nexus_layer is not None
    assert runner.nexus_layer.digest() == result.nexus_layer.digest()
