"""task-14: branches restored from one fork payload must be genuinely independent.

The reviewer finding was that two branches built from one ``capture_fork()``
payload shared the same ``PopulationState`` and ``ElementGrid`` objects, that the
branch reported ``fork_state_exact = False`` while ``fork_audit_payload()``
reported ``True``, and that the old test asserted the false report.  These tests
discriminate the real behaviour:

* distinct objects per branch (population, element grid);
* an in-place ATP / population mutation in branch A is invisible to branch B and
  to the parent, and the converse;
* the audit payload reflects the actual state of the branch it describes, and is
  not a constant: forcing an uncopyable object flips it to False and makes
  ``from_fork`` refuse loudly instead of sharing state.
"""

from __future__ import annotations

import json

import pytest

from codontrace.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.errors import ConfigurationError

SEED = 31


def _spec() -> GenesisExperimentSpec:
    return GenesisExperimentSpec(tick_count=0, seed=SEED)


def _parent(ticks: int = 3) -> GenesisEngine:
    engine = GenesisEngine.from_spec(_spec())
    engine.run_ticks(ticks)
    return engine


def _first_organism(engine: GenesisEngine):
    return engine.runner.population.organisms[0]


def _atp(engine: GenesisEngine) -> float:
    return float(_first_organism(engine).atp_state.runtime.current_atp)


def _branches():
    parent = _parent()
    payload = parent.capture_fork()
    arm_a = GenesisEngine.from_fork(_spec(), payload)
    arm_b = GenesisEngine.from_fork(_spec(), payload)
    return parent, arm_a, arm_b


def test_two_branches_from_one_payload_are_not_the_same_objects() -> None:
    parent, arm_a, arm_b = _branches()

    assert arm_a.runner.population is not arm_b.runner.population
    assert arm_a.runner.population is not parent.runner.population
    if parent.element_grid is not None:
        assert arm_a.element_grid is not arm_b.element_grid
        assert arm_a.element_grid is not parent.element_grid

    # the branch itself and its audit must agree, and both must be truthful
    assert arm_a.fork_state_exact is True
    audit = arm_a.fork_audit_payload()
    assert audit["fork_state_exact"] is True
    assert audit["fork_isolation"] == arm_a.fork_isolation
    assert audit["fork_isolation"]["population"] == "deepcopy"
    assert json.dumps(audit)


def _first_grid_cell_amount(engine: GenesisEngine) -> float | None:
    grid = engine.element_grid
    if grid is None or not grid.cells:  # pragma: no cover - spec dependent
        return None
    position = sorted(grid.cells)[0]
    amounts = grid.cells[position]
    symbol = sorted(amounts)[0]
    return float(amounts[symbol])


def _bump_first_grid_cell(engine: GenesisEngine, delta: float) -> None:
    """Mutate the element grid in place (a cell amount) for this branch only."""

    grid = engine.element_grid
    if grid is None or not grid.cells:  # pragma: no cover - spec dependent
        return
    position = sorted(grid.cells)[0]
    amounts = grid.cells[position]
    symbol = sorted(amounts)[0]
    amounts[symbol] = float(amounts[symbol]) + delta


def test_mutating_branch_a_leaves_branch_b_and_the_parent_untouched() -> None:
    parent, arm_a, arm_b = _branches()

    b_before, parent_before = _atp(arm_b), _atp(parent)
    b_grid_before, parent_grid_before = (
        _first_grid_cell_amount(arm_b),
        _first_grid_cell_amount(parent),
    )
    organism_a = _first_organism(arm_a)
    organism_a.atp_state.runtime.current_atp += 7.5
    organism_a.vitae_store += 1.25
    _bump_first_grid_cell(arm_a, 9.0)

    assert _atp(arm_a) != b_before
    assert _atp(arm_b) == b_before
    assert _atp(parent) == parent_before
    if b_grid_before is not None:
        assert _first_grid_cell_amount(arm_a) != b_grid_before
        assert _first_grid_cell_amount(arm_b) == b_grid_before
        assert _first_grid_cell_amount(parent) == parent_grid_before


def test_mutating_branch_b_leaves_branch_a_and_the_parent_untouched() -> None:
    parent, arm_a, arm_b = _branches()

    a_before, parent_before = _atp(arm_a), _atp(parent)
    a_grid_before, parent_grid_before = (
        _first_grid_cell_amount(arm_a),
        _first_grid_cell_amount(parent),
    )
    organism_b = _first_organism(arm_b)
    organism_b.atp_state.runtime.current_atp += 3.25
    organism_b.vitae_store += 0.5
    _bump_first_grid_cell(arm_b, 4.5)

    assert _atp(arm_b) != a_before
    assert _atp(arm_a) == a_before
    assert _atp(parent) == parent_before
    if a_grid_before is not None:
        assert _first_grid_cell_amount(arm_b) != a_grid_before
        assert _first_grid_cell_amount(arm_a) == a_grid_before
        assert _first_grid_cell_amount(parent) == parent_grid_before


def test_audit_reports_the_actual_state_and_refuses_when_isolation_is_impossible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import codontrace.engine_runtime as runtime

    parent = _parent()

    # 1. the healthy case: computed from this branch, all present objects copied
    audit = parent.fork_audit_payload()
    assert isinstance(audit["fork_isolation"], dict)
    assert audit["fork_isolation"]["population"] == "deepcopy"
    assert audit["fork_state_exact"] is True

    # 2. force the population copy to fail: the audit must report the real state
    #    (this is what the old constant `exact_state: True` hid) ...
    real = runtime._isolated_copy

    def refuse_population(value: object) -> object:
        if type(value).__name__ == "PopulationState":
            raise TypeError("synthetic mappingproxy blocker")
        return real(value)

    monkeypatch.setattr(runtime, "_isolated_copy", refuse_population)

    degraded = parent.fork_audit_payload()
    assert degraded["fork_isolation"]["population"] == "shared_reference"
    assert degraded["fork_state_exact"] is False

    # ... and a branch must refuse loudly rather than silently share state
    with pytest.raises(ConfigurationError, match="fork isolation refused"):
        GenesisEngine.from_fork(_spec(), parent.capture_fork())
