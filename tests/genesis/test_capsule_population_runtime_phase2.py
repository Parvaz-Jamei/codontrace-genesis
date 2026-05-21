from codontrace.genesis import (
    CapsuleTransferConfig,
    CausalGraph,
    CausalGraphConfig,
    GenesisOrganism,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
    step_population,
)
from codontrace.world import World2D


def _population(*organisms: GenesisOrganism) -> PopulationState:
    return PopulationState(generation=0, tick=0, organisms=tuple(organisms), lineage=(), fitness=())


def test_capsule_transfer_off_preserves_zero_metrics() -> None:
    emitter = GenesisOrganism.from_bits("a", "110", initial_runtime_atp=5.0, position=(1, 1))
    result = step_population(
        _population(emitter),
        World2D(width=5, height=5),
        PopulationConfigs(
            reproduction=ReproductionConfig(enabled=False),
            enable_nexus_stigmergy=False,
            capsule_transfer=CapsuleTransferConfig(enabled=False),
        ),
    )

    assert result.nexus_layer is None
    assert result.organism_records[0].capsules_emitted == 0
    assert result.causal_summary.capsules_emitted == 0


def test_emit_nexus_deposits_capsule_and_nearby_organism_adopts() -> None:
    emitter = GenesisOrganism.from_bits(
        "a",
        "110",
        initial_runtime_atp=5.0,
        initial_learning_atp=2.0,
        position=(1, 1),
        causal_graph=CausalGraph(CausalGraphConfig(update_cost=0.0)),
    )
    reader = GenesisOrganism.from_bits(
        "b",
        "000",
        initial_runtime_atp=5.0,
        initial_learning_atp=2.0,
        position=(2, 1),
        causal_graph=CausalGraph(CausalGraphConfig(update_cost=0.0)),
    )
    config = CapsuleTransferConfig(
        enabled=True,
        min_confidence=0.0,
        emission_cost_runtime_atp=0.0,
        emission_cost_learning_atp=0.0,
        read_cost_runtime_atp=0.0,
        adoption_cost_learning_atp=0.5,
        read_radius=1,
    )

    result = step_population(
        _population(emitter, reader),
        World2D(width=5, height=5),
        PopulationConfigs(
            reproduction=ReproductionConfig(enabled=False),
            enable_nexus_stigmergy=True,
            capsule_transfer=config,
        ),
    )

    assert result.nexus_layer is not None
    assert len(result.nexus_layer.signals) == 1
    records = {record.organism_id: record for record in result.organism_records}
    assert records["a"].capsules_emitted == 1
    assert records["b"].capsules_read == 1
    assert records["b"].capsules_adopted == 1
    assert records["b"].capsule_adoption_failures == 0
    assert result.causal_summary.capsules_adopted == 1
    assert result.causal_summary.organisms_with_graph == 2


def test_distant_organism_does_not_read_capsule_outside_radius() -> None:
    emitter = GenesisOrganism.from_bits(
        "a",
        "110",
        initial_runtime_atp=5.0,
        initial_learning_atp=1.0,
        position=(1, 1),
        causal_graph=CausalGraph(CausalGraphConfig(update_cost=0.0)),
    )
    distant = GenesisOrganism.from_bits(
        "b",
        "000",
        initial_runtime_atp=5.0,
        initial_learning_atp=1.0,
        position=(4, 4),
        causal_graph=CausalGraph(CausalGraphConfig(update_cost=0.0)),
    )
    result = step_population(
        _population(emitter, distant),
        World2D(width=6, height=6),
        PopulationConfigs(
            reproduction=ReproductionConfig(enabled=False),
            enable_nexus_stigmergy=True,
            capsule_transfer=CapsuleTransferConfig(
                enabled=True,
                min_confidence=0.0,
                emission_cost_runtime_atp=0.0,
                emission_cost_learning_atp=0.0,
                read_cost_runtime_atp=0.0,
                adoption_cost_learning_atp=0.5,
                read_radius=1,
            ),
        ),
    )

    records = {record.organism_id: record for record in result.organism_records}
    assert records["b"].capsules_read == 0
    assert records["b"].capsules_adopted == 0


def test_adoption_with_insufficient_learning_atp_fails_without_graph_change() -> None:
    emitter = GenesisOrganism.from_bits(
        "a",
        "110",
        initial_runtime_atp=5.0,
        initial_learning_atp=1.0,
        position=(1, 1),
        causal_graph=CausalGraph(CausalGraphConfig(update_cost=0.0)),
    )
    reader_graph = CausalGraph(CausalGraphConfig(update_cost=0.0))
    reader = GenesisOrganism.from_bits(
        "b",
        "000",
        initial_runtime_atp=5.0,
        initial_learning_atp=0.1,
        position=(2, 1),
        causal_graph=reader_graph,
    )
    before = reader_graph.digest()

    result = step_population(
        _population(emitter, reader),
        World2D(width=5, height=5),
        PopulationConfigs(
            reproduction=ReproductionConfig(enabled=False),
            enable_nexus_stigmergy=True,
            capsule_transfer=CapsuleTransferConfig(
                enabled=True,
                min_confidence=0.0,
                emission_cost_runtime_atp=0.0,
                emission_cost_learning_atp=0.0,
                read_cost_runtime_atp=0.0,
                adoption_cost_learning_atp=1.0,
                read_radius=1,
            ),
        ),
    )

    records = {record.organism_id: record for record in result.organism_records}
    assert records["b"].capsules_read == 1
    assert records["b"].capsules_adopted == 0
    assert records["b"].capsule_adoption_failures == 1
    assert records["b"].causal_graph_digest_before == before
