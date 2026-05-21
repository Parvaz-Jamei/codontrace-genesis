from __future__ import annotations

import json

import pytest

from codontrace import (
    CodonTraceError,
    InvalidDensityError,
    InvalidWorldSizeError,
    ResourceConfig,
    ScenarioAgentProfile,
    ScenarioConfig,
    ScenarioFactory,
    ScenarioValidationError,
    Trace,
    TraceEvent,
    WorldConfig,
    WorldEvent,
    WorldFactory,
)
from codontrace.trace import (
    WORLD_EVENT_AGENT_MOVED,
    WORLD_EVENT_AGENT_REGISTERED,
    WORLD_EVENT_AGENT_REMOVED,
    WORLD_EVENT_SNAPSHOT_MARKER,
)
from codontrace.world import World2D


def _compact_genomes(config: ScenarioConfig) -> tuple[str, ...]:
    scenario = ScenarioFactory.from_config(config)
    return tuple(agent.genome.to_compact() for agent in scenario.agents)


def _codon_coverage(genomes: tuple[str, ...]) -> int:
    codons: set[str] = set()
    for genome in genomes:
        codons.update(genome[index : index + 3] for index in range(0, len(genome), 3))
    return len(codons)


def test_public_validation_errors_are_codontrace_errors() -> None:
    assert issubclass(InvalidDensityError, CodonTraceError)
    assert issubclass(InvalidWorldSizeError, CodonTraceError)
    assert issubclass(ScenarioValidationError, CodonTraceError)


def test_world_and_scenario_contract_public_names_roundtrip() -> None:
    config = ScenarioConfig(
        name="contract",
        seed=17,
        world=WorldConfig(
            width=12,
            height=12,
            seed=17,
            boundary="wrap",
            wall_density=0.05,
            wall_pattern="rooms",
            resource_density=0.08,
            resource_distribution="uniform",
            resource_amount_range=(2.0, 4.0),
            allow_resource_on_wall=False,
            allow_agent_on_wall=False,
        ),
        agents=(ScenarioAgentProfile(name="collector", count=2),),
        max_steps=25,
        trace_enabled=True,
        replay_enabled=True,
        metadata={"purpose": "qa"},
    )

    restored = ScenarioConfig.from_json(config.to_json())

    assert restored == config
    assert restored.config_hash == config.config_hash
    assert restored.agents == config.agents
    assert restored.profiles == config.agents
    assert restored.max_steps == 25
    assert restored.steps == 25
    assert restored.metadata == {"purpose": "qa"}


def test_world_config_rejects_invalid_size_and_contradictory_density() -> None:
    with pytest.raises(InvalidWorldSizeError):
        WorldConfig(width=0, height=8)
    with pytest.raises(InvalidDensityError):
        WorldConfig(width=8, height=8, wall_density=0.1, wall_pattern="none")
    with pytest.raises(InvalidDensityError):
        WorldConfig(width=8, height=8, resource_density=0.1, resource_distribution="none")
    with pytest.raises(InvalidDensityError):
        WorldConfig(width=8, height=8, hazard_density=0.1, hazard_distribution="none")
    with pytest.raises(InvalidDensityError):
        WorldConfig(width=8, height=8, beacon_density=0.1, beacon_distribution="none")
    with pytest.raises(ScenarioValidationError):
        WorldConfig(width=8, height=8, resource_amount_range=(3.0, 1.0))


def test_resource_and_obstacle_configs_are_first_class_inputs() -> None:
    resources = ResourceConfig(
        kind="food",
        density=0.1,
        amount_range=(4.0, 4.0),
        distribution="uniform",
        respawn=True,
        respawn_rate=0.1,
    )
    world = WorldFactory.from_config(
        WorldConfig(width=10, height=10, seed=3, boundary="open", resource_config=resources)
    )

    assert world.resources
    assert set(world.resources.values()) == {4.0}


def test_rooms_pattern_deterministic_and_overlap_prevention() -> None:
    config = WorldConfig(
        width=14,
        height=14,
        seed=4,
        boundary="open",
        wall_density=0.1,
        wall_pattern="rooms",
        resource_density=0.2,
        resource_distribution="uniform",
        hazard_density=0.1,
        hazard_distribution="uniform",
        beacon_density=0.1,
        beacon_distribution="uniform",
    )
    world_a = WorldFactory.from_config(config)
    world_b = WorldFactory.from_config(config)

    assert world_a.digest() == world_b.digest()
    assert world_a.walls
    assert set(world_a.resources).isdisjoint(world_a.walls)
    assert all(position not in world_a.walls for position in world_a.objects)


def test_resource_amount_range_is_deterministic() -> None:
    config = WorldConfig(
        width=12,
        height=12,
        seed=9,
        boundary="open",
        resource_density=0.2,
        resource_distribution="uniform",
        resource_amount_range=(1.0, 5.0),
    )
    world_a = WorldFactory.from_config(config)
    world_b = WorldFactory.from_config(config)

    assert world_a.digest() == world_b.digest()
    assert world_a.resources
    assert all(1.0 <= amount <= 5.0 for amount in world_a.resources.values())


def test_scenario_genome_strategies_are_real_and_distinct() -> None:
    base_world = WorldConfig(width=16, height=16, seed=21, boundary="open")
    bias = {bits: 0.0 for bits in ("000", "001", "010", "011", "100", "101", "110", "111")}
    bias["111"] = 1.0
    configs = {
        strategy: ScenarioConfig(
            name=strategy,
            seed=21,
            world=base_world,
            agents=(
                ScenarioAgentProfile(
                    name="p",
                    count=8,
                    genome_strategy=strategy,
                    genome_length_range=(4, 4),
                    codon_bias=bias,
                ),
            ),
        )
        for strategy in (
            "uniform_random",
            "profiled_random",
            "lineage_seeded",
            "latin_hypercube_lite",
        )
    }
    genomes = {strategy: _compact_genomes(config) for strategy, config in configs.items()}

    assert len(set(tuple(values) for values in genomes.values())) == 4
    assert all(set(genome) <= {"1"} for genome in genomes["profiled_random"])
    lineage = ScenarioFactory.from_config(configs["lineage_seeded"])
    assert lineage.agents[0].lineage_id == "p"
    assert lineage.agents[1].parent_id == "p-000"
    assert lineage.agents[1].generation == 1
    assert _codon_coverage(genomes["latin_hypercube_lite"]) >= _codon_coverage(
        genomes["uniform_random"]
    )


def test_traceevent_replay_reference_fields_roundtrip() -> None:
    event = TraceEvent(
        step=0,
        agent_id="a1",
        codon="000",
        action="WAIT",
        atp_before=1.0,
        atp_after=0.9,
        position_before=(1, 1),
        position_after=(1, 1),
        genome_digest="genome-x",
        world_digest_before="world-y",
        cause_refs=("cause:1",),
        config_hash="config-z",
    )
    restored = TraceEvent.from_dict(event.to_dict())

    assert restored.genome_digest == "genome-x"
    assert restored.world_digest_before == "world-y"
    assert restored.cause_refs == ("cause:1",)
    assert restored.config_hash == "config-z"


def test_trace_from_bundle_rejects_duplicate_step_sequence() -> None:
    trace = Trace()
    for agent_id in ("a", "b"):
        trace.append(
            TraceEvent(
                step=0,
                agent_id=agent_id,
                codon="000",
                action="WAIT",
                atp_before=1.0,
                atp_after=0.9,
                position_before=(0, 0),
                position_after=(0, 0),
            )
        )
    bundle = trace.to_bundle()
    timeline = bundle["timeline"]
    assert isinstance(timeline, list)
    assert isinstance(timeline[1], dict)
    timeline[1]["sequence"] = timeline[0]["sequence"]

    from codontrace.errors import ReplayError

    with pytest.raises(ReplayError):
        Trace.from_bundle(bundle)


def test_official_timeline_only_world_events_are_safe_noops() -> None:
    world = World2D(5, 5)
    for event_type in (
        WORLD_EVENT_AGENT_REGISTERED,
        WORLD_EVENT_AGENT_MOVED,
        WORLD_EVENT_AGENT_REMOVED,
        WORLD_EVENT_SNAPSHOT_MARKER,
    ):
        event = WorldEvent(schema_version=1, step=0, sequence=0, event_type=event_type)
        world.apply_world_event(event)

    assert world.digest() == World2D(5, 5).digest()


def test_scenario_config_hash_stable_after_json_roundtrip_and_factory() -> None:
    config = ScenarioConfig(
        seed=31,
        world=WorldConfig(width=10, height=10, seed=31, boundary="open"),
        agents=(ScenarioAgentProfile(name="a", count=3),),
        metadata={"label": "stable"},
    )
    restored = ScenarioConfig.from_json(config.to_json())
    scenario_a = ScenarioFactory.from_config(config)
    scenario_b = ScenarioFactory.from_config(restored)

    assert restored.config_hash == config.config_hash
    assert scenario_a.initial_world_digest == scenario_b.initial_world_digest
    assert scenario_a.initial_agent_digest == scenario_b.initial_agent_digest
    assert json.loads(config.to_json())["agents"][0]["name"] == "a"
