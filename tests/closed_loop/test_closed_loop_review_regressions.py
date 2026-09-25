"""Regressions for the two confirmed defects, plus the output contract.

The uniform band below was fixed before the seeded shuffler was run.
Four parents and two windows have three equally likely pairings, and two
of those three are heterotypic, so the expected heterotypic count in 48
seeds is 32. The acceptance window is 24 to 40, about mean ± 2.6 standard
deviations of Binomial(48, 2/3). A rule that follows identity order lands
on 0 or 48 and is outside that window.
"""

from __future__ import annotations

import json

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_p6 import (
    _spawn,
    _tape,
    classify_oscillation,
    classify_oscillation_v1,
    digest_matches,
    mate_outcross,
    run_match_arm,
    run_shared_modifier,
)
from codontrace.genesis.host_parasite_life_plugin import OUTCROSS_OUT_BITS
from codontrace.rng import RNGManager

_SEEDS = range(48)
_HETEROTYPIC_LOW = 24
_HETEROTYPIC_HIGH = 40


def _parent(identifier: str, window: str):
    return _spawn(identifier, _tape(OUTCROSS_OUT_BITS, window), 10.0)


def _children(identifiers: tuple[str, ...], windows: tuple[str, ...], seed: int):
    parents = [_parent(identifier, window) for identifier, window in zip(identifiers, windows, strict=True)]
    children, unmated = mate_outcross(
        parents,
        generation=0,
        atp=10.0,
        mate_choice="random",
        recombine=True,
        rng=RNGManager(seed=seed, namespace="review-mating"),
    )
    return tuple(sorted(child.genome.to_compact()[-6:] for child in children)), unmated


def _heterotypic(identifiers: tuple[str, ...], windows: tuple[str, ...]) -> int:
    recombinant = ("000000", "000000", "111111", "111111")
    return sum(
        1
        for seed in _SEEDS
        if _children(identifiers, windows, seed)[0] == recombinant
    )


def test_random_pairs_are_not_a_function_of_identity_order() -> None:
    grouped = ("h0", "h1", "h2", "h3")
    windows = ("000111", "000111", "111000", "111000")
    interleaved_ids = ("h0", "h1", "h2", "h3")
    interleaved_windows = ("000111", "111000", "000111", "111000")
    grouped_count = _heterotypic(grouped, windows)
    interleaved_count = _heterotypic(interleaved_ids, interleaved_windows)
    assert _HETEROTYPIC_LOW <= grouped_count <= _HETEROTYPIC_HIGH
    assert _HETEROTYPIC_LOW <= interleaved_count <= _HETEROTYPIC_HIGH
    ordered_like, _ = mate_outcross(
        [_parent(identifier, window) for identifier, window in zip(grouped, windows, strict=True)],
        generation=0,
        atp=10.0,
        mate_choice="ordered",
        recombine=True,
    )
    ordered_mix, _ = mate_outcross(
        [
            _parent(identifier, window)
            for identifier, window in zip(interleaved_ids, interleaved_windows, strict=True)
        ],
        generation=0,
        atp=10.0,
        mate_choice="ordered",
        recombine=True,
    )
    assert [child.genome.to_compact()[-6:] for child in ordered_like] != [
        child.genome.to_compact()[-6:] for child in ordered_mix
    ]


def test_mating_counts_cover_empty_singleton_odd_and_even() -> None:
    def draw(n: int, seed: int = 1):
        parents = [_parent(f"h{index}", "000111" if index % 2 == 0 else "111000") for index in range(n)]
        return mate_outcross(
            parents,
            generation=0,
            atp=10.0,
            rng=RNGManager(seed=seed, namespace="review-count"),
        )

    children, unmated = draw(0)
    assert children == [] and unmated == 0
    children, unmated = draw(1)
    assert children == [] and unmated == 1
    children, unmated = draw(2)
    assert len(children) == 2 and unmated == 0
    children, unmated = draw(3)
    assert len(children) == 2 and unmated == 1
    children, unmated = draw(4)
    assert len(children) == 4 and unmated == 0
    again, _ = draw(4, seed=1)
    assert [child.genome.to_compact() for child in children] == [
        child.genome.to_compact() for child in again
    ]


def test_extinction_after_two_returns_is_not_stable() -> None:
    host_a = (("000111", 2),)
    host_b = (("111000", 2),)
    empty: tuple[tuple[str, int], ...] = ()
    parasite_p = (("000111", 12),)
    parasite_q = (("111000", 12),)
    hosts = (host_a, host_b, host_a, host_b, host_a, empty, empty, empty)
    parasites = (parasite_p, parasite_q, parasite_q, parasite_q, parasite_q, parasite_q, parasite_q, parasite_q)
    debits = (1, 1, 1, 1, 1, 1, 1, 1)
    assert classify_oscillation(hosts, parasites, debits) == "extinct"
    assert classify_oscillation_v1(hosts, parasites, debits) == "stable"


def test_an_early_parasite_change_does_not_make_the_host_orbit_stable() -> None:
    host_a = (("000111", 2),)
    host_b = (("111000", 2),)
    parasite_p = (("000111", 12),)
    parasite_q = (("111000", 12),)
    hosts = (host_a, host_b, host_a, host_b, host_a)
    parasites = (parasite_p, parasite_q, parasite_q, parasite_q, parasite_q)
    assert classify_oscillation(hosts, parasites, (1, 1, 1, 1, 1)) == "decoupled"


def test_shared_record_round_trips_and_detects_tampering() -> None:
    record = run_shared_modifier(
        (("selfing", "000111"), ("outcross", "111000")),
        passage="absent",
        virulence=1.0,
        generations=2,
        seed=4,
        birth_atp=10.0,
    )
    payload = record.to_dict()
    assert payload["birth_atp"] == 10.0
    assert payload["mate_choice"] == "random"
    assert payload["recombine"] is True
    assert payload["revision"]
    assert payload["founders"] == [["selfing", "000111"], ["outcross", "111000"]]
    assert digest_matches(record)
    assert json.loads(json.dumps(payload)) == payload
    forged = dict(payload)
    forged["birth_atp"] = 11.0
    from codontrace.genesis.closed_loop_p6 import _record_digest

    assert _record_digest(forged) != payload["digest"]
    again = run_shared_modifier(
        (("selfing", "000111"), ("outcross", "111000")),
        passage="absent",
        virulence=1.0,
        generations=2,
        seed=4,
        birth_atp=10.0,
    )
    assert again.to_dict() == payload
    other = run_shared_modifier(
        (("selfing", "000111"), ("outcross", "111000")),
        passage="absent",
        virulence=1.0,
        generations=2,
        seed=4,
        birth_atp=12.0,
    )
    assert other.digest != record.digest
    with pytest.raises(ConfigurationError):
        run_match_arm(mating="selfing", passage="absent", virulence=float("nan"))


def test_numeric_refusals_cover_both_paths() -> None:
    bad = (
        {"virulence": float("nan")},
        {"virulence": float("inf")},
        {"virulence": float("-inf")},
        {"birth_atp": float("nan")},
        {"parasite_mutation": 1.1},
        {"parasite_mutation": -0.1},
        {"generations": True},
        {"generations": 0},
        {"birth_atp": 0.0},
        {"seed": -1},
    )
    for kwargs in bad:
        arm_kwargs = {"virulence": 1.0, **kwargs}
        with pytest.raises(ConfigurationError):
            run_match_arm(mating="selfing", passage="absent", **arm_kwargs)  # type: ignore[arg-type]
        with pytest.raises(ConfigurationError):
            run_shared_modifier((("selfing", "000111"),), passage="absent", **arm_kwargs)  # type: ignore[arg-type]
    edge = run_match_arm(
        mating="selfing", passage="frozen", virulence=32.0, generations=2, parasite_mutation=0.0
    )
    assert edge.parasite_window == "000111"
    upper = run_match_arm(
        mating="selfing", passage="frozen", virulence=32.0, generations=2, parasite_mutation=1.0
    )
    assert upper.parasite_window == "000111"
    with pytest.raises(ConfigurationError):
        classify_oscillation(((),), ((),), ())
    with pytest.raises(ConfigurationError):
        classify_oscillation(((),), ((),), (-1,))

