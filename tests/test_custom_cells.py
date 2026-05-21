from __future__ import annotations

import pytest

from codontrace import World2D


def test_custom_cell_marker_from_ascii() -> None:
    world = World2D.from_ascii("A.X", allow_custom_cells=True)
    assert world.get_custom_cell((2, 0)) == "X"
    assert world.get_cell((2, 0)) == "X"


def test_unknown_ascii_cells_require_allow_custom_cells() -> None:
    with pytest.raises(ValueError):
        World2D.from_ascii("A.X")


def test_set_custom_cell_marker() -> None:
    world = World2D(3, 1)
    world.set_custom_cell((2, 0), "X")
    assert world.get_custom_cell((2, 0)) == "X"
