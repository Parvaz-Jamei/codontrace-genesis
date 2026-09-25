"""Confirmatory seeds 101–108. The locked bar is 6 of 8. This run does not clear it."""

from __future__ import annotations

from pathlib import Path

from codontrace.genesis.closed_loop_confirmatory import (
    CONFIRMATORY_SEEDS,
    mixed_seed,
    run_confirmatory_partial,
)

_REPO = Path(__file__).resolve().parents[2]


def test_confirmatory_blocks_fail_and_the_flag_stays_false() -> None:
    report = run_confirmatory_partial()
    assert tuple(row.seed for row in report.separate) == CONFIRMATORY_SEEDS
    assert tuple(row.seed for row in report.mixed) == CONFIRMATORY_SEEDS
    assert tuple(row.passed for row in report.separate) == (
        False,
        True,
        False,
        False,
        False,
        False,
        False,
        False,
    )
    assert report.separate_passes == 1
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
