from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from codontrace import RNGManager


def test_rng_manager_is_deterministic_and_forkable() -> None:
    left = RNGManager(seed=42)
    right = RNGManager(seed=42)
    assert [left.randrange(100) for _ in range(5)] == [right.randrange(100) for _ in range(5)]
    assert left.fork("mutation").snapshot() == {
        "seed": 42,
        "namespace": "root/mutation",
        "draw_count": 0,
    }


def test_rng_snapshot_restore_resumes_exact_stream_without_pickle() -> None:
    rng = RNGManager(seed=7)
    _ = [rng.randrange(10) for _ in range(5)]
    snapshot = rng.snapshot(include_state=True)
    json.dumps(snapshot)
    restored = RNGManager.restore(snapshot)
    assert rng.randrange(10) == restored.randrange(10)
    assert rng.draw_count == restored.draw_count
    assert rng.state_digest() == restored.state_digest()


def test_rng_restore_rejects_invalid_snapshot() -> None:
    with pytest.raises(ValueError, match="Invalid RNG snapshot"):
        RNGManager.restore({"seed": 1})


def test_no_direct_random_usage_outside_rng_module() -> None:
    src = Path(__file__).resolve().parents[1] / "src" / "codontrace"
    forbidden = ("import random", "from random", "random.", "Random(", "pickle")
    offenders: list[str] = []
    for path in src.rglob("*.py"):
        if path.name == "rng.py":
            continue
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            if marker in text:
                offenders.append(f"{path.relative_to(src)}:{marker}")
    assert offenders == []


def test_rng_manager_shuffle_in_place_and_multiset_preservation() -> None:
    rng = RNGManager(seed=123)

    # In-place identity check: list modified in-place
    original_list = [10, 20, 30, 40, 50]
    list_ref = original_list
    rng.shuffle(original_list)

    assert original_list is list_ref
    assert sorted(original_list) == [10, 20, 30, 40, 50]
    assert original_list != [10, 20, 30, 40, 50]

    # Multiset preservation with duplicate elements and heterogeneous types
    mixed: list[object] = ["a", "b", "a", "c", "b", "d", 42, 42]
    original_counts = Counter(mixed)
    rng.shuffle(mixed)
    assert Counter(mixed) == original_counts


def test_rng_manager_shuffle_draw_count_accounting() -> None:
    rng = RNGManager(seed=999)

    # For length N >= 2, draw_count must increase by exactly N - 1
    for length in (2, 3, 4, 5, 10, 25, 100):
        items = list(range(length))
        initial_draws = rng.draw_count
        rng.shuffle(items)
        assert rng.draw_count - initial_draws == length - 1


def test_rng_manager_shuffle_boundary_edge_cases() -> None:
    rng = RNGManager(seed=777)

    # Empty list: remains empty, exactly 0 draws consumed
    empty: list[int] = []
    initial_draws = rng.draw_count
    rng.shuffle(empty)
    assert empty == []
    assert rng.draw_count == initial_draws

    # Single-element list: remains unchanged, exactly 0 draws consumed
    single = [42]
    initial_draws = rng.draw_count
    rng.shuffle(single)
    assert single == [42]
    assert rng.draw_count == initial_draws

    # Two-element list: exactly 1 draw consumed
    pair = [1, 2]
    initial_draws = rng.draw_count
    rng.shuffle(pair)
    assert rng.draw_count - initial_draws == 1
    assert sorted(pair) == [1, 2]

    # Uniform items list
    uniform_items = [9, 9, 9, 9]
    initial_draws = rng.draw_count
    rng.shuffle(uniform_items)
    assert uniform_items == [9, 9, 9, 9]
    assert rng.draw_count - initial_draws == 3


def test_rng_manager_shuffle_deterministic_reproducibility() -> None:
    rng1 = RNGManager(seed=42, namespace="benchmark")
    rng2 = RNGManager(seed=42, namespace="benchmark")

    seq1 = list(range(20))
    seq2 = list(range(20))

    rng1.shuffle(seq1)
    rng2.shuffle(seq2)

    assert seq1 == seq2
    assert rng1.draw_count == rng2.draw_count


def test_rng_manager_shuffle_statistical_uniformity() -> None:
    rng = RNGManager(seed=2026)
    trials = 60_000
    expected_freq = trials / 6.0

    permutation_counts: Counter[tuple[int, ...]] = Counter()
    position_counts: list[Counter[int]] = [Counter(), Counter(), Counter()]

    for _ in range(trials):
        items = [0, 1, 2]
        rng.shuffle(items)
        permutation_counts[tuple(items)] += 1
        for pos, val in enumerate(items):
            position_counts[pos][val] += 1

    # All 6 permutations must appear
    assert len(permutation_counts) == 6

    # Pearson chi-square goodness-of-fit test for uniform distribution:
    # Under H0, chi2 ~ chi2(df=5). Critical value at p=0.001 is 20.52.
    chi2 = sum((count - expected_freq) ** 2 / expected_freq for count in permutation_counts.values())
    assert chi2 < 20.52, f"Chi-square statistic {chi2:.2f} exceeds critical value 20.52"

    # Empirical probability bounds per permutation: ~ 1/6 (0.1667)
    for perm, count in permutation_counts.items():
        prob = count / trials
        assert 0.150 <= prob <= 0.185, f"Permutation {perm} probability {prob:.4f} outside [0.150, 0.185]"

    # Position-level marginal uniformity: each element in each slot ~ 1/3 (0.3333)
    for pos in range(3):
        for val in range(3):
            val_prob = position_counts[pos][val] / trials
            assert 0.315 <= val_prob <= 0.350, f"Value {val} at position {pos} prob {val_prob:.4f} outside bounds"
