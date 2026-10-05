"""Ledger demography must match the antagonist population that produced it."""

from __future__ import annotations

from codontrace.genesis.closed_loop_hp_arm01 import ARM_FIXED
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import StructuralRQArm
from codontrace.genesis.measurements.antagonist_population import (
    ANTAGONIST_ECOLOGY_POPULATION,
)


def test_passage_ledger_matches_population_births_and_deaths() -> None:
    arm = StructuralRQArm.boot_structural(
        arm=ARM_FIXED,
        seed=601,
        antagonist_ecology=ANTAGONIST_ECOLOGY_POPULATION,
    )
    assert arm.passage == "frozen"
    previous = {unit.unit_id: unit.window for unit in arm.antagonist_pop.units}
    founder_windows = [unit.window for unit in arm.antagonist_pop.units]
    arm.run_generations(1)
    first_snapshot = [
        (unit.unit_id, unit.window, unit.energy)
        for unit in arm.antagonist_unit_series[0]
    ]
    arm.run_generations(1)
    assert [
        (unit.unit_id, unit.window, unit.energy)
        for unit in arm.antagonist_unit_series[0]
    ] == first_snapshot

    for index, (ledger, snap) in enumerate(
        zip(arm.antagonist_pop.ledgers, arm.antagonist_unit_series, strict=True)
    ):
        current = {unit.unit_id: unit.window for unit in snap}
        born = set(current) - set(previous)
        died = set(previous) - set(current)
        assert {unit.unit_id for unit in ledger.newborns} == born
        assert set(ledger.deaths) == died
        assert len(ledger.deaths) == len(died)
        assert set(ledger.deaths).isdisjoint(current)
        assert len(ledger.kept) + len(ledger.newborns) == len(snap)
        row = arm.antagonist_ledger[index]
        assert row == (
            len(ledger.kept),
            len(ledger.newborns),
            int(ledger.mutation_events),
            len(died),
        )
        assert ledger.mutation_events == 0
        assert [unit.window for unit in snap] == founder_windows
        previous = current
