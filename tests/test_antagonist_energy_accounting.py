"""split_v2 antagonist energy and identity invariants.

The archived RQ-3 tables stay as results of the previous, defective accounting.
These tests are the acceptance check for the corrected contract.
"""

from __future__ import annotations

import math

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.measurements.antagonist_population import (
    ACCOUNTING_VERSION,
    AntagonistPopulation,
    AntagonistUnit,
    ContactEvent,
)
from codontrace.rng import RNGManager


def _population(energies: tuple[float, ...], windows: tuple[str, ...] | None = None) -> AntagonistPopulation:
    labels = windows or tuple(f"w{i}" for i in range(len(energies)))
    units = [
        AntagonistUnit(
            unit_id=f"a0-{i}",
            window=labels[i],
            parent_id=None,
            born_generation=0,
            energy=energy,
        )
        for i, energy in enumerate(energies)
    ]
    return AntagonistPopulation(
        units=units,
        seat_cap=len(units),
        ancestral_windows=list(labels),
        mutation_rate=0.0,
        maintenance_cost=0.15,
        fecundity=1.0,
    )


def _advance(pop: AntagonistPopulation, *, seed: int, mode: str, generation: int = 1, **kwargs):
    return pop.advance(
        matched_windows=(),
        mode=mode,
        generation=generation,
        rng=RNGManager(seed=seed, namespace=f"acct/{mode}/{generation}"),
        mutate_window=lambda window, _rng: window,
        **kwargs,
    )


def _independent_residual(account) -> float:
    """Balance written out here, not by calling EnergyAccount.residual."""

    return (
        account.opening
        + account.contact_income
        - account.maintenance_loss
        - account.death_loss
        - account.eviction_loss
        - account.reproduction_cost
        - account.closing
    )


def test_reported_reproduction_does_not_create_energy() -> None:
    for mode in ("coevolve", "frozen", "shuffled_labels"):
        pop = _population((2.0, 0.7, 0.1))
        opening = 2.8
        _advance(pop, seed=1, mode=mode)
        closing = sum(unit.energy for unit in pop.units)
        assert closing <= opening
        assert closing != pytest.approx(3.7)
        account = pop.energy_accounts[-1]
        assert account.contact_income == 0.0
        assert abs(_independent_residual(account)) < 1e-9
        assert abs(account.residual()) < 1e-9
        assert pop.accounting_version == ACCOUNTING_VERSION


def test_frozen_reseat_is_one_to_one() -> None:
    pop = _population((2.0, 1.0, 0.1))
    _advance(pop, seed=2, mode="frozen")
    ids = [unit.unit_id for unit in pop.units]
    assert len(ids) == len(set(ids))
    assert ids.count("a0-1") <= 1
    assert [unit.window for unit in pop.units] == ["w0", "w1", "w2"][: len(pop.units)]


def test_same_window_income_follows_the_serving_unit() -> None:
    pop = _population((1.0, 1.0), windows=("AA", "AA"))
    pop.fecundity = 0.0
    event = ContactEvent("c1", "host-7", "a0-1", 2.0, window="AA")
    _advance(pop, seed=3, mode="coevolve", contact_events=(event,), served_contacts=(("AA", 2.0),))
    by_id = {unit.unit_id: unit.energy for unit in pop.units}
    assert "a0-1" in by_id
    assert by_id["a0-1"] > by_id.get("a0-0", 0.0)
    account = pop.energy_accounts[-1]
    assert account.contact_income == pytest.approx(0.5 * 2.0)
    assert abs(_independent_residual(account)) < 1e-9


def test_multi_offspring_split_debits_the_parent() -> None:
    pop = _population((2.0,))
    pop.fecundity = 2.0
    pop.seat_cap = 8
    _advance(pop, seed=4, mode="coevolve")
    energies = {unit.unit_id: unit.energy for unit in pop.units}
    assert "a0-0" in energies
    children = [unit for unit in pop.units if unit.parent_id == "a0-0"]
    assert len(children) >= 2
    assert abs(sum(unit.energy for unit in pop.units) - (2.0 - 0.15)) < 1e-9
    assert all(unit.parent_id in pop.known_unit_ids for unit in children)


def test_starvation_removes_energy_as_maintenance() -> None:
    pop = _population((0.1,))
    _advance(pop, seed=5, mode="coevolve")
    assert pop.units == []
    account = pop.energy_accounts[-1]
    assert account.maintenance_loss == pytest.approx(0.1)
    assert account.death_loss == 0.0
    assert account.closing == 0.0
    assert pop.ledgers[-1].deaths == ("a0-0",)
    assert abs(_independent_residual(account)) < 1e-9


@pytest.mark.parametrize(
    "builder",
    [
        lambda: _population((math.nan,)),
        lambda: _population((math.inf,)),
        lambda: AntagonistPopulation.founders(("w",), mutation_rate=1.5),
        lambda: AntagonistPopulation.founders(("w",), fecundity=-1.0),
        lambda: AntagonistPopulation.founders(("w",), maintenance_cost=0.0),
    ],
)
def test_out_of_range_parameters_are_rejected(builder) -> None:
    with pytest.raises(ConfigurationError):
        builder()


def test_negative_and_unknown_contacts_are_rejected() -> None:
    pop = _population((1.0,))
    with pytest.raises(ConfigurationError):
        _advance(
            pop,
            seed=6,
            mode="coevolve",
            contact_events=(ContactEvent("c", "h", "a0-0", -1.0),),
        )
    pop = _population((1.0,))
    with pytest.raises(ConfigurationError):
        _advance(
            pop,
            seed=6,
            mode="coevolve",
            contact_events=(ContactEvent("c", "h", "missing", 1.0),),
        )


def test_hypothesis_is_installed_for_the_energy_property() -> None:
    import hypothesis

    assert hypothesis.__version__


def test_property_balance_identity_and_parents() -> None:
    pytest.importorskip("hypothesis")
    from hypothesis import given
    from hypothesis import strategies as st

    @given(
        energies=st.lists(st.floats(min_value=0.0, max_value=3.0, allow_nan=False), min_size=1, max_size=4),
        seed=st.integers(min_value=0, max_value=40),
        mode=st.sampled_from(("coevolve", "frozen", "shuffled_labels")),
        generations=st.integers(min_value=1, max_value=4),
    )
    def _check(energies: list[float], seed: int, mode: str, generations: int) -> None:
        pop = _population(tuple(energies))
        history = set(pop.known_unit_ids)
        for generation in range(1, generations + 1):
            before = sum(unit.energy for unit in pop.units)
            _advance(pop, seed=seed, mode=mode, generation=generation)
            account = pop.energy_accounts[-1]
            assert abs(_independent_residual(account)) < 1e-8
            assert sum(unit.energy for unit in pop.units) <= before + 1e-8
            ids = [unit.unit_id for unit in pop.units]
            assert len(ids) == len(set(ids))
            for unit in pop.units:
                if unit.parent_id is not None:
                    assert unit.parent_id in history
                history.add(unit.unit_id)

    _check()


def test_unassigned_payment_and_bad_parents_are_rejected() -> None:
    pop = _population((1.0,))
    with pytest.raises(ConfigurationError, match="no antagonist unit"):
        _advance(pop, seed=7, mode="coevolve", served_contacts=(("missing", 1.0),))
    assert pop.units[0].energy == 1.0
    assert pop.energy_accounts == []

    with pytest.raises(ConfigurationError, match="no history"):
        AntagonistPopulation(
            units=[AntagonistUnit("a0-0", "w", "ghost", 0, energy=1.0)],
            seat_cap=1,
            ancestral_windows=["w"],
        )
    with pytest.raises(ConfigurationError, match="own parent"):
        AntagonistPopulation(
            units=[AntagonistUnit("a0-0", "w", "a0-0", 0, energy=1.0)],
            seat_cap=1,
            ancestral_windows=["w"],
        )


def test_corpse_energy_is_booked_as_death() -> None:
    pop = _population((1.0, 0.4))
    pop.units[1] = AntagonistUnit(
        unit_id="a0-1",
        window="w1",
        parent_id=None,
        born_generation=0,
        energy=0.4,
        alive=False,
    )
    pop.fecundity = 0.0
    _advance(pop, seed=8, mode="coevolve")
    account = pop.energy_accounts[-1]
    assert account.death_loss == pytest.approx(0.4)
    assert abs(_independent_residual(account)) < 1e-9
    assert [unit.unit_id for unit in pop.units] == ["a0-0"]


def test_failed_generation_does_not_keep_new_ids() -> None:
    pop = _population((1.0,))
    with pytest.raises(ConfigurationError):
        _advance(
            pop,
            seed=9,
            mode="coevolve",
            contact_events=(
                ContactEvent("c", "h", "a0-0", 1.0),
                ContactEvent("c", "h", "a0-0", 1.0),
            ),
        )
    assert pop.known_unit_ids == {"a0-0"}
    assert pop.pre_selection_signatures == []
    assert pop.units[0].energy == 1.0
