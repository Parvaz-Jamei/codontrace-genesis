"""Confirmatory seeds 101–108. The locked bar is 6 of 8. This run does not clear it."""

from __future__ import annotations

from pathlib import Path

from codontrace.genesis.closed_loop_confirmatory import (
    CONFIRMATORY_SEEDS,
    graded_block,
    locked_flag,
    mixed_seed,
    run_confirmatory_partial,
    run_sensitivity,
    separate_seed,
)

_REPO = Path(__file__).resolve().parents[2]


def test_confirmatory_blocks_fail_and_the_flag_stays_false() -> None:
    report = run_confirmatory_partial()
    assert tuple(row.seed for row in report.separate) == CONFIRMATORY_SEEDS
    assert tuple(row.seed for row in report.mixed) == CONFIRMATORY_SEEDS
    assert tuple(row.passed for row in report.separate) == (False,) * 8
    assert report.separate_passes == 0
    assert report.separate_block is False
    assert tuple(row.passed for row in report.mixed) == (False,) * 8
    assert report.mixed_passes == 0
    assert report.mixed_block is False
    assert all(row.unmated_at_0 == 0 for row in report.mixed)
    assert all(row.frozen_outcross == 0 for row in report.mixed)
    assert report.graded_ran is False
    assert report.red_queen_proved is False
    assert report.biological_red_queen_proved is False
    again = mixed_seed(101)
    assert again.to_dict() == report.mixed[0].to_dict()
    engine = (_REPO / "src" / "codontrace" / "engine.py").read_text(encoding="utf-8").lower()
    for token in ("outcross", "infection", "parasite", "red_queen", "matching_allele"):
        assert token not in engine


def test_graded_overlap_removes_the_outcross_arm() -> None:
    rows = graded_block()
    assert tuple(row.seed for row in rows) == CONFIRMATORY_SEEDS
    assert all(row.specificity == "graded" for row in rows)
    assert all(row.passed is False for row in rows)
    assert all(row.outcross_coevolve_extinct for row in rows)
    assert all(row.outcross_frozen_cycles is False for row in rows)
    assert locked_flag(1, 0, 0) is False
    one = separate_seed(101, specificity="graded")
    assert one.to_dict() == separate_seed(101, specificity="graded").to_dict()


def test_sensitivity_shifts_with_birth_atp_and_stays_under_the_bar() -> None:
    cells = run_sensitivity()
    assert max(cell.conjunction for cell in cells) == 0
    assert not any(cell.conjunction >= 6 for cell in cells)

    def first_majority(birth_atp: float) -> float:
        return min(
            cell.virulence
            for cell in cells
            if cell.birth_atp == birth_atp and cell.selfing_coevolve_extinct >= 6
        )

    assert first_majority(8.0) == 16.0
    assert first_majority(10.0) == 20.0
    assert first_majority(12.0) == 24.0
    for birth_atp in (8.0, 10.0, 12.0):
        plateau = next(
            cell for cell in cells if cell.birth_atp == birth_atp and cell.virulence == 32.0
        )
        assert plateau.selfing_coevolve_extinct == 6
        assert plateau.outcross_coevolve_cycles == 0
        assert plateau.conjunction == 0
    low = next(cell for cell in cells if cell.birth_atp == 10.0 and cell.virulence == 8.0)
    assert low.outcross_coevolve_cycles == 4
    assert low.selfing_coevolve_extinct == 0
    assert low.conjunction == 0
    assert locked_flag(0, 0, 0) is False
