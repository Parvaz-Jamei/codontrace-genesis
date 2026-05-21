from __future__ import annotations

import pytest

from codontrace import ConfigurationError, World2D


def test_world_movement_boundaries_resources_and_digest() -> None:
    world = World2D.from_ascii("""
...
.A*
..#
""")
    assert world.move_agent((1, 1), (1, 0)) == ((2, 1), "moved")
    assert world.collect_resource((2, 1)) == 2.0
    assert world.move_agent((2, 1), (0, 1)) == ((2, 1), "wall_blocked")
    assert len(world.digest()) == 64


def test_world_from_ascii_accepts_f_as_resource_alias() -> None:
    world = World2D.from_ascii("""
...
.AF
...
""")
    assert world.get_cell((2, 1)) == World2D.RESOURCE


def test_world_from_ascii_accepts_indented_triple_quoted_map() -> None:
    world = World2D.from_ascii(
        """
        ....
        .A*.
        ..#.
        """
    )

    assert world.width == 4
    assert world.height == 3
    assert world.agent_position == (1, 1)
    assert world.get_cell((2, 1)) == World2D.RESOURCE
    assert world.is_wall((2, 2))


def test_world_from_ascii_still_rejects_truly_uneven_rows() -> None:
    with pytest.raises(ConfigurationError, match="same width"):
        World2D.from_ascii(
            """
            ....
            .A*.
            ..#
            """
        )


def test_world_from_ascii_preserves_placement_after_dedent() -> None:
    world = World2D.from_ascii(
        """
            A..
            .*.
            ..#
        """
    )

    assert world.agent_position == (0, 0)
    assert world.resources == {(1, 1): 2.0}
    assert world.walls == {(2, 2)}


def test_world_set_cell_accepts_f_resource_alias() -> None:
    world = World2D(3, 3)
    world.set_cell((1, 1), "F")
    assert world.get_cell((1, 1)) == World2D.RESOURCE


def test_movement_delta_unknown_action_has_clear_error() -> None:
    with pytest.raises(ValueError, match="Unknown movement action"):
        World2D.movement_delta("UNKNOWN")
