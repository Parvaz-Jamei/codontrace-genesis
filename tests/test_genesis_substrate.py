from __future__ import annotations

import pytest

from codontrace.genesis import ElementGrid, ElementKind


def test_grid_creation_is_deterministic_and_digest_stable() -> None:
    left = ElementGrid(2, 2)
    right = ElementGrid(2, 2)
    assert left.to_dict() == right.to_dict()
    assert left.digest() == right.digest()


def test_invalid_dimensions_fail_clearly() -> None:
    with pytest.raises(ValueError):
        ElementGrid(0, 1)
    with pytest.raises(ValueError):
        ElementGrid(True, 1)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ElementGrid(1, 1, tick=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ElementGrid(1, 1, tick=-1)


def test_step_advances_tick_by_one() -> None:
    grid = ElementGrid(1, 1)
    result = grid.step()
    assert result.tick == 1
    assert grid.tick == 1


def test_basic_emergence_rules_produce_expected_elements_with_conserved_total() -> None:
    grid = ElementGrid.from_cells(
        1,
        1,
        {
            (0, 0): {
                ElementKind.IGNIS: 3.0,
                ElementKind.AETHER: 3.0,
                ElementKind.TERRA: 3.0,
                ElementKind.AQUA: 3.0,
                ElementKind.LUMEN: 3.0,
                ElementKind.VITAE: 3.0,
                ElementKind.UMBRA: 3.0,
            }
        },
    )
    before = grid.total_energy()
    result = grid.step()
    assert result.changed_cells == 1
    assert grid.amount((0, 0), ElementKind.LUMEN) > 0
    assert grid.amount((0, 0), ElementKind.AQUA) > 0
    assert grid.amount((0, 0), ElementKind.UMBRA) > 0
    assert grid.amount((0, 0), ElementKind.VITAE) > 0
    assert grid.amount((0, 0), ElementKind.NEXUS) > 0
    assert abs(before - grid.total_energy()) <= 1e-9


def test_grid_to_dict_from_dict_roundtrip() -> None:
    grid = ElementGrid.from_cells(1, 1, {(0, 0): {ElementKind.IGNIS: 2.0}})
    restored = ElementGrid.from_dict(grid.to_dict())
    assert restored.to_dict() == grid.to_dict()
    assert restored.digest() == grid.digest()
