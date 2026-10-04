"""Phase-1 gates. Two repeated histories are not twelve, and a label is not a witness."""

from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.rq_mechanism_v2_phase5 import VERDICT_BLOCKED, VERDICT_NOT_DECLARED, VERDICT_SUPPORTED
from codontrace.genesis.rq_reciprocal_validity import assess_independent_histories

WINDOW_A = "000000"
WINDOW_B = "111111"


def _generation(generation: int, *, gap: float, births_a: int = 2, births_b: int = 1) -> dict[str, object]:
    births = [{"parent_window": WINDOW_A} for _ in range(births_a)]
    births += [{"parent_window": WINDOW_B} for _ in range(births_b)]
    return {
        "generation": generation,
        "host_births": births,
        "host_deaths": [],
        "selection_gap": gap,
        "start_windows": [WINDOW_A, WINDOW_A, WINDOW_B, WINDOW_B],
    }


def _history(seed: int, *, gap_start: float = 0.2, gap_end: float = -0.2) -> dict[str, object]:
    # The gap carries the seed so twelve histories are not one body repeated.
    return {
        "generations": [
            _generation(1, gap=gap_start + seed / 100000.0),
            _generation(2, gap=gap_end - seed / 100000.0),
        ],
        "history_id": f"hist-{seed}",
        "reversal": True,
        "fitness_measured": False,
        "seed": seed,
    }


def test_boolean_label_cannot_declare_and_repeated_histories_cannot_fill_n() -> None:
    seeds = list(range(9911, 9923))
    one = _history(9911)
    other = _history(9912, gap_start=-0.4, gap_end=0.4)
    other["history_id"] = "hist-9912"
    with pytest.raises(ConfigurationError, match="duplicate history"):
        assess_independent_histories([one, dict(one)], seeds, importance_bound=0.2)
    cloned = dict(one)
    cloned["seed"] = 9912
    cloned["history_id"] = "hist-copy"
    with pytest.raises(ConfigurationError, match="duplicate history"):
        assess_independent_histories([one, cloned], seeds, importance_bound=0.2)
    relabeled = dict(one)
    with pytest.raises(ConfigurationError, match="duplicate history_id"):
        assess_independent_histories([one, relabeled], seeds, importance_bound=None)
    doubled = list(seeds) + [9911]
    with pytest.raises(ConfigurationError, match="duplicate seeds"):
        assess_independent_histories([_history(seed) for seed in seeds], doubled, importance_bound=None)
    broken = _history(9911)
    broken["generations"] = list(broken["generations"]) + [dict(broken["generations"][0])]
    with pytest.raises(ConfigurationError, match="duplicate generations"):
        assess_independent_histories([broken], seeds, importance_bound=None)


def test_label_only_history_is_not_a_valid_sample_and_cannot_prove_red_queen() -> None:
    seeds = list(range(9911, 9923))
    labeled = []
    for seed in seeds:
        labeled.append(
            {
                "fitness_measured": True,
                "generations": [{"generation": 1, "selection_gap": float(seed)}],
                "history_id": f"label-{seed}",
                "reversal": True,
                "seed": seed,
            }
        )
    report = assess_independent_histories(labeled, seeds, importance_bound=0.2)
    assert report["n_independent"] == 0
    assert report["n_independent"] != 12
    assert report["verdict"] == VERDICT_BLOCKED
    assert report["interval"] is None
    assert report["red_queen_proved"] is False
    assert report["used_boolean_label"] is False
    full = [_history(seed) for seed in seeds]
    scored = assess_independent_histories(full, seeds, importance_bound=None)
    assert scored["n_independent"] == 12
    assert scored["measurement_floor"] == 12
    assert scored["verdict"] != VERDICT_SUPPORTED
    assert scored["supported_forbidden"] is True
    assert scored["red_queen_proved"] is False
    # Every archived gap changes sign, so the rate is 12/12. Importance is still required.
    declared = assess_independent_histories(full, seeds, importance_bound=0.5)
    assert declared["reversal_true_n"] == 12
    assert declared["interval"]["lower"] > 0.5
    assert declared["interval"]["upper"] == 1.0
    assert declared["verdict"] == VERDICT_SUPPORTED
    assert declared["red_queen_proved"] is False
    assert declared["verdict"] != VERDICT_NOT_DECLARED
