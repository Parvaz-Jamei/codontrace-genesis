from __future__ import annotations

import pytest

from codontrace import (
    AgentFactory,
    AgentProfile,
    AgentSpec,
    Codon,
    CodonTable,
    InitializationConfig,
    LineageConfig,
    SemanticGenome,
    World2D,
)


def test_manual_specs_create_agents() -> None:
    agents = AgentFactory.from_specs(
        [
            AgentSpec(
                agent_id="explorer-1",
                genome=SemanticGenome.from_codons(["101", "001"]),
                initial_atp=4.0,
                position=(1, 1),
                profile="explorer",
            )
        ]
    )

    assert len(agents) == 1
    assert agents[0].id == "explorer-1"
    assert agents[0].profile == "explorer"
    assert agents[0].position == (1, 1)


def test_duplicate_agent_ids_fail() -> None:
    spec = AgentSpec(
        agent_id="a",
        genome=SemanticGenome.from_codons(["000"]),
        initial_atp=1.0,
        position=(0, 0),
    )
    with pytest.raises(ValueError, match="Duplicate agent_id"):
        AgentFactory.from_specs([spec, spec])


def test_uniform_random_is_deterministic_with_seed() -> None:
    world = World2D(width=6, height=4)
    config = InitializationConfig(count=5, seed=42, placement_strategy="uniform_random")

    left = AgentFactory.create_many(world=world, config=config)
    right = AgentFactory.create_many(world=world, config=config)

    assert [(agent.position, agent.genome.to_codons()) for agent in left] == [
        (agent.position, agent.genome.to_codons()) for agent in right
    ]


def test_different_seeds_change_generated_agents() -> None:
    world = World2D(width=6, height=4)
    left = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(count=5, seed=1, placement_strategy="uniform_random"),
    )
    right = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(count=5, seed=2, placement_strategy="uniform_random"),
    )

    assert [(agent.position, agent.genome.to_codons()) for agent in left] != [
        (agent.position, agent.genome.to_codons()) for agent in right
    ]


def test_profiled_random_creates_exact_counts_per_profile() -> None:
    world = World2D(width=10, height=8)
    agents = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(
            count=6,
            seed=7,
            genome_strategy="profiled_random",
            placement_strategy="grid",
            profiles=(
                AgentProfile(name="explorer", count=2, preferred_codons=("101",)),
                AgentProfile(name="collector", count=4, preferred_codons=("111",)),
            ),
        ),
    )

    assert [agent.profile for agent in agents].count("explorer") == 2
    assert [agent.profile for agent in agents].count("collector") == 4


def test_preferred_codons_bias_appears_in_generated_genomes() -> None:
    world = World2D(width=8, height=8)
    agents = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(
            count=3,
            seed=5,
            genome_strategy="profiled_random",
            placement_strategy="grid",
            profiles=(
                AgentProfile(
                    name="conserver",
                    count=3,
                    genome_length=5,
                    preferred_codons=("000",),
                    preferred_codons_weight=1.0,
                ),
            ),
        ),
    )

    assert all(agent.genome.to_codons() == ("000", "000", "000", "000", "000") for agent in agents)


def test_profiles_with_weights_divide_count_deterministically() -> None:
    world = World2D(width=10, height=10)
    agents = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(
            count=10,
            seed=3,
            genome_strategy="profiled_random",
            placement_strategy="grid",
            profiles=(
                AgentProfile(name="explorer", weight=2.0),
                AgentProfile(name="collector", weight=1.0),
                AgentProfile(name="conserver", weight=1.0),
            ),
        ),
    )

    profiles = [agent.profile for agent in agents]
    assert profiles.count("explorer") == 5
    assert profiles.count("collector") + profiles.count("conserver") == 5


def test_poisson_disk_respects_min_distance() -> None:
    world = World2D(width=8, height=8)
    agents = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(
            count=5,
            seed=11,
            placement_strategy="poisson_disk",
            min_distance=2,
        ),
    )

    positions = [agent.position for agent in agents]
    for index, left in enumerate(positions):
        for right in positions[index + 1 :]:
            assert max(abs(left[0] - right[0]), abs(left[1] - right[1])) >= 2


def test_grid_placement_is_deterministic() -> None:
    world = World2D(width=3, height=3)
    agents = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(count=4, placement_strategy="grid"),
    )

    assert [agent.position for agent in agents] == [(0, 0), (1, 0), (2, 0), (0, 1)]


def test_no_spawn_on_walls_or_resources() -> None:
    world = World2D.from_ascii("""
#*.
...
""")
    agents = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(count=2, seed=9, placement_strategy="grid"),
    )

    assert [agent.position for agent in agents] == [(2, 0), (0, 1)]


def test_capacity_errors_are_clear() -> None:
    world = World2D(width=2, height=2)
    with pytest.raises(ValueError, match="Cannot place"):
        AgentFactory.create_many(
            world=world,
            config=InitializationConfig(
                count=4,
                seed=1,
                placement_strategy="poisson_disk",
                min_distance=2,
            ),
        )


def test_lineage_seeded_records_lineage_and_parent() -> None:
    world = World2D(width=6, height=6)
    agents = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(
            count=4,
            seed=12,
            genome_strategy="lineage_seeded",
            placement_strategy="grid",
        ),
    )

    assert agents[0].generation == 0
    assert all(agent.lineage_id == "lineage-default" for agent in agents)
    assert all(agent.parent_id == agents[0].id for agent in agents[1:])
    assert all(agent.generation == 1 for agent in agents[1:])


def test_generated_agents_can_run_one_step() -> None:
    world = World2D(width=4, height=4)
    agent = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(count=1, seed=4, placement_strategy="grid"),
    )[0]

    trace = agent.run(world, steps=1)
    assert len(trace) == 1


def test_invalid_preferred_codon_fails() -> None:
    world = World2D(width=4, height=4)
    with pytest.raises(ValueError, match="invalid preferred codons"):
        AgentFactory.create_many(
            world=world,
            config=InitializationConfig(
                count=1,
                genome_strategy="profiled_random",
                profiles=(AgentProfile(name="bad", count=1, preferred_codons=("222",)),),
            ),
        )


def test_profile_count_overflow_fails() -> None:
    world = World2D(width=4, height=4)
    with pytest.raises(ValueError, match="exceed requested count"):
        AgentFactory.create_many(
            world=world,
            config=InitializationConfig(
                count=1,
                profiles=(
                    AgentProfile(name="a", count=1),
                    AgentProfile(name="b", count=1),
                ),
            ),
        )


def test_latin_hypercube_strategy_runs_without_extra_dependency() -> None:
    world = World2D(width=5, height=5)
    agents = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(
            count=4,
            seed=21,
            genome_strategy="latin_hypercube",
            placement_strategy="grid",
        ),
    )

    assert len(agents) == 4
    assert len({agent.genome.to_compact() for agent in agents}) >= 2


def test_profile_placement_zone_is_respected() -> None:
    world = World2D(width=5, height=5)
    agents = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(
            count=2,
            seed=1,
            placement_strategy="grid",
            profiles=(AgentProfile(name="corner", count=2, placement_zone=(2, 2, 4, 4)),),
        ),
    )

    assert all(x >= 2 and y >= 2 for x, y in [agent.position for agent in agents])


def test_manual_unknown_codon_fails_against_table() -> None:
    custom_table = CodonTable((Codon("000", "WAIT", 0.0),))
    with pytest.raises(ValueError, match="not present"):
        AgentFactory.from_specs(
            [
                AgentSpec(
                    agent_id="x",
                    genome=SemanticGenome.from_codons(["001"]),
                    initial_atp=1.0,
                    position=(0, 0),
                )
            ],
            codon_table=custom_table,
        )


def test_latin_hypercube_rejects_multiple_profiles() -> None:
    world = World2D(width=6, height=6)
    with pytest.raises(ValueError, match="exactly one profile"):
        AgentFactory.create_many(
            world=world,
            config=InitializationConfig(
                count=4,
                seed=22,
                genome_strategy="latin_hypercube",
                placement_strategy="grid",
                profiles=(
                    AgentProfile(name="left", count=2),
                    AgentProfile(name="right", count=2),
                ),
            ),
        )


def test_lineage_config_controls_ancestor_count() -> None:
    world = World2D(width=8, height=8)
    agents = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(
            count=5,
            seed=13,
            genome_strategy="lineage_seeded",
            placement_strategy="grid",
            lineage_config=LineageConfig(
                ancestor_count=2, mutation_operations=("point",), mutation_steps=2
            ),
        ),
    )

    ancestors = [agent for agent in agents if agent.parent_id is None]
    children = [agent for agent in agents if agent.parent_id is not None]
    assert len(ancestors) == 2
    assert len(children) == 3
    assert all(child.generation == 2 for child in children)


def test_lineage_config_validates_mutation_operations() -> None:
    world = World2D(width=4, height=4)
    with pytest.raises(ValueError, match="Invalid lineage mutation operations"):
        AgentFactory.create_many(
            world=world,
            config=InitializationConfig(
                count=2,
                genome_strategy="lineage_seeded",
                placement_strategy="grid",
                lineage_config=LineageConfig(mutation_operations=("explode",)),
            ),
        )


def test_from_specs_validates_world_bounds_when_world_provided() -> None:
    world = World2D(width=3, height=3)
    spec = AgentSpec(
        agent_id="a1",
        genome=SemanticGenome.from_codons(["000"]),
        initial_atp=1.0,
        position=(9, 9),
    )
    with pytest.raises(ValueError, match="outside the world"):
        AgentFactory.from_specs([spec], world=world)


def test_from_specs_rejects_wall_position_when_world_provided() -> None:
    world = World2D.from_ascii("###\n#.#\n###")
    spec = AgentSpec(
        agent_id="a1",
        genome=SemanticGenome.from_codons(["000"]),
        initial_atp=1.0,
        position=(0, 0),
    )
    with pytest.raises(ValueError, match="wall"):
        AgentFactory.from_specs([spec], world=world)


def test_capacity_error_mentions_requested_placed_candidates() -> None:
    world = World2D(width=2, height=2)
    with pytest.raises(ValueError) as exc_info:
        AgentFactory.create_many(
            world=world,
            config=InitializationConfig(
                count=4,
                seed=1,
                placement_strategy="poisson_disk",
                min_distance=2,
            ),
        )
    message = str(exc_info.value)
    assert "Cannot place 4 agents" in message
    assert "placed" in message
    assert "candidate cells" in message
