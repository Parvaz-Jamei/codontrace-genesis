from __future__ import annotations

from codontrace.genesis.behavior import BehaviorDescriptorBuilder, BehaviorMetricRegistry
from codontrace.genesis.fitness import GenesisFitnessV1
from codontrace.genesis.liveness import AliveGateConfig
from codontrace.genesis.organism import GenesisOrganism
from codontrace.world import World2D


def test_behavior_registry_and_fitness_breakdown_are_auditable() -> None:
    organism = GenesisOrganism.from_bits("o", "000000000", initial_runtime_atp=5.0)
    run = organism.run(World2D(3, 3), ticks=3, alive_config=AliveGateConfig(min_ticks=1))
    registry = BehaviorMetricRegistry.genesis_v1().register(
        "custom_constant", lambda descriptor, context=None: 7
    )
    values = BehaviorDescriptorBuilder(registry).build(
        run.trace, run.alive_result, organism.atp_state
    )
    assert values["custom_constant"] == 7.0
    breakdown = GenesisFitnessV1(genome_length_penalty=0.01).evaluate(
        trace=run.trace,
        alive_result=run.alive_result,
        genome_length=len(organism.genome.to_compact()),
    )
    assert breakdown.digest()
    assert any(item.name == "genome_length_penalty" for item in breakdown.components)
