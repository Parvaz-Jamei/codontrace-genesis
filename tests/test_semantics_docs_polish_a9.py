from __future__ import annotations

from pathlib import Path

import tomllib

from codontrace import (
    ObstacleConfig,
    ResourceConfig,
    ScenarioConfig,
    Trace,
    WhiteBoxAgent,
    WorldConfig,
    WorldFactory,
)

ROOT = Path(__file__).resolve().parents[1]


def test_obstacle_block_flags_are_preserved_metadata_not_runtime_movement() -> None:
    config = WorldConfig(
        width=5,
        height=5,
        seed=5,
        boundary="closed",
        obstacle_config=ObstacleConfig(
            density=0.0,
            pattern="none",
            block_movement=False,
            block_sight=False,
        ),
    )
    restored = WorldConfig.from_dict(config.to_dict())

    assert restored.obstacle_config.block_movement is False
    assert restored.obstacle_config.block_sight is False

    world = WorldFactory.from_config(restored)
    agent = WhiteBoxAgent.quick(genome="110", initial_atp=3.0, position=(1, 1))
    event = agent.step(world, Trace())

    assert world.is_wall((0, 1))
    assert event.reason == "wall_blocked"
    assert event.position_after == (1, 1)
    assert agent.position == (1, 1)


def test_resource_kind_is_preserved_metadata_while_world_resources_remain_amount_only() -> None:
    food_config = WorldConfig(
        width=5,
        height=5,
        seed=12,
        boundary="open",
        resource_config=ResourceConfig(
            kind="food",
            density=0.4,
            amount_range=(3.0, 3.0),
            distribution="uniform",
        ),
    )
    mineral_config = WorldConfig(
        width=5,
        height=5,
        seed=12,
        boundary="open",
        resource_config=ResourceConfig(
            kind="mineral",
            density=0.4,
            amount_range=(3.0, 3.0),
            distribution="uniform",
        ),
    )

    assert (
        ScenarioConfig(seed=12, world=food_config).config_hash
        != ScenarioConfig(seed=12, world=mineral_config).config_hash
    )

    world = WorldFactory.from_config(food_config)

    assert food_config.resource_config.kind == "food"
    assert world.resources
    assert all(isinstance(amount, float) for amount in world.resources.values())
    assert set(world.resources.values()) == {3.0}
    assert world.objects == {}


def test_docs_state_config_metadata_runtime_boundaries() -> None:
    docs = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in ("README.md", "docs/api.md", "docs/concepts.md", "RELEASE_EVIDENCE.md")
    )

    assert "Generated `World2D.resources` remain amount-only" in docs
    assert "not represented per resource cell" in docs
    assert "Use `WorldObject.kind`" in docs
    assert "do not change default movement or sensing behavior yet" in docs
    assert "Default movement still treats `World2D.walls` as blocking cells" in docs
    assert "no line-of-sight physics or raycasting" in docs


def test_pyproject_uses_modern_license_metadata_without_legacy_license_classifier() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]

    assert project["license"] == "MIT"
    assert project["license-files"] == ["LICENSE"]
    assert "License :: OSI Approved :: MIT License" not in project["classifiers"]
