from __future__ import annotations

from codontrace.genesis import (
    AliveGateConfig,
    EpisodicMemory,
    FitnessConfig,
    GenesisATPState,
    MutationConfig,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
    step_population,
)
from codontrace.genesis.organism import GenesisOrganism
from codontrace.world import World2D


def test_population_records_memory_and_learning_audit_fields() -> None:
    organism = GenesisOrganism.from_bits("o", "000", initial_runtime_atp=5.0, position=(1, 1))
    organism.atp_state = GenesisATPState.from_runtime(5.0, learning_atp=1.0, learning_enabled=True)
    organism.episodic_memory = EpisodicMemory()
    configs = PopulationConfigs(
        reproduction=ReproductionConfig(max_population=2),
        mutation=MutationConfig(bit_flip_rate=0.0),
        fitness=FitnessConfig(),
        alive_gate=AliveGateConfig(
            min_ticks=1,
            min_executed_actions=0,
            require_positive_runtime_atp=False,
        ),
        ticks_per_generation=1,
    )
    result = step_population(
        PopulationState(0, 0, (organism,), (), ()),
        World2D(3, 3),
        configs,
        seed=1,
    )
    record = result.organism_records[0]

    assert record.memory_digest_before is not None
    assert record.memory_digest_after is not None
    assert record.memory_write_count == 1
    assert record.learning_ledger_digest_before is not None
    assert record.learning_ledger_digest_after is not None
    assert record.behavior_descriptor is not None
    assert record.from_dict(record.to_dict()).to_dict() == record.to_dict()
