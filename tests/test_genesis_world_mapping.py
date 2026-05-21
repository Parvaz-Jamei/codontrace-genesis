from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis import ElementKind, element_grid_to_world2d, world2d_to_element_grid
from codontrace.world import World2D


def test_world2d_maps_supported_cells_to_elements() -> None:
    world = World2D.from_ascii(
        """
        .#*
        IVU
        N..
        """,
        allow_custom_cells=True,
    )
    grid = world2d_to_element_grid(world)
    assert grid.amount((0, 0), ElementKind.AETHER) == 1.0
    assert grid.amount((1, 0), ElementKind.TERRA) == 1.0
    assert grid.amount((2, 0), ElementKind.LUMEN) == 2.0
    assert grid.amount((0, 1), ElementKind.IGNIS) == 1.0
    assert grid.amount((1, 1), ElementKind.VITAE) == 1.0
    assert grid.amount((2, 1), ElementKind.UMBRA) == 1.0
    assert grid.amount((0, 2), ElementKind.NEXUS) == 1.0


def test_world_mapping_roundtrip_preserves_supported_cells() -> None:
    world = World2D.from_ascii(
        """
        .#*
        IVU
        N..
        """,
        allow_custom_cells=True,
    )
    restored = element_grid_to_world2d(world2d_to_element_grid(world))
    assert restored.render_ascii() == world.render_ascii()


def test_unsupported_custom_cell_fails_clearly() -> None:
    world = World2D.from_ascii("X", allow_custom_cells=True)
    with pytest.raises(ConfigurationError):
        world2d_to_element_grid(world)
