"""Regression: a sexual birth record must name the parents of the child genome."""

from __future__ import annotations

from codontrace.genesis.birth import (
    ReproductionMode,
    SexualRecombinationConfig,
    apply_positional_segment_swap,
)
from codontrace.genesis.liveness import AliveGateConfig
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import (
    MutationConfig,
    OffspringPlacementPolicy,
    PopulationConfigs,
    PopulationState,
    ReproductionConfig,
    step_population,
)
from codontrace.world import World2D


def test_two_fold_birth_trace_parents_rebuild_the_child_genome() -> None:
    """The completing parent must not overwrite the backbone parent on the birth trace.

    TWO_FOLD_COST_SEX places one recombinant. The trace used to store the actor
    as both parent_id and second_parent_id, so the recorded window could not
    rebuild the child.
    """

    world = World2D(4, 4)
    parent_a = GenesisOrganism.from_bits(
        "a", "111000000", initial_runtime_atp=20.0, position=(0, 0)
    )
    parent_b = GenesisOrganism.from_bits(
        "b", "111111000", initial_runtime_atp=20.0, position=(0, 1)
    )
    configs = PopulationConfigs(
        reproduction=ReproductionConfig(
            min_runtime_atp=1.0,
            parent_atp_cost=1.0,
            max_population=8,
            offspring_placement=OffspringPlacementPolicy.SAME_CELL,
            reproduction_mode=ReproductionMode.SEXUAL_CROSSOVER,
        ),
        mutation=MutationConfig(bit_flip_rate=0.0),
        alive_gate=AliveGateConfig(
            min_ticks=1,
            min_executed_actions=0,
            max_blocked_ratio=1.0,
            require_positive_runtime_atp=True,
        ),
        sexual_recombination=SexualRecombinationConfig(
            enabled=True,
            recombination_prob=1.0,
            chamber_capacity=8,
            two_fold_cost_sex=True,
        ),
    )
    born = step_population(
        PopulationState(0, 0, (parent_a, parent_b), (), ()),
        world,
        configs,
        seed=8,
    )
    assert born.births == 1
    events = [
        event
        for trace in born.traces
        for event in trace.events
        if event.action == "COPY_SELF" and event.world_delta.get("reproduction_succeeded") is True
    ]
    assert len(events) == 1
    delta = events[0].world_delta
    parent_id = delta["parent_id"]
    second_parent_id = delta["second_parent_id"]
    assert parent_id != second_parent_id
    assert delta["parent_ids"] == [parent_id, second_parent_id]
    bits = {organism.id: organism.genome.to_compact() for organism in born.population.organisms}
    child_id = delta["child_id"]
    assert isinstance(child_id, str)
    expected = apply_positional_segment_swap(
        bits[str(parent_id)],
        bits[str(second_parent_id)],
        int(delta["recombination_start_index"]),
        int(delta["recombination_end_index"]),
    )
    assert bits[child_id] == expected
    lineage = next(record for record in born.population.lineage if record.organism_id == child_id)
    assert lineage.mutation_count == 0
    assert lineage.parent_ids == (parent_id, second_parent_id)
    assert bits[child_id] == apply_positional_segment_swap(
        bits[lineage.parent_id],
        bits[str(lineage.second_parent_id)],
        int(lineage.recombination_start_index),
        int(lineage.recombination_end_index),
    )
