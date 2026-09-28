"""De-toy D0+D1: type-II / diagonally-dominant RQ stepper on HP port."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_type2_rq import (
    SCHEMA,
    assert_diagonally_dominant,
    assert_no_super_host_or_parasite,
    build_diagonally_dominant_A,
    build_graded_A_from_repertoires,
    graded_alpha_from_overlap,
    run_type2_campaign,
    run_type2_cycling_trial,
)

ROOT = Path(__file__).resolve().parents[1]
PIN_SPECS = (
    (
        "docs/hard_experiment_01/results_v7.json",
        "35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6",
    ),
    (
        "docs/claimgate/risk_bar.json",
        "4dbe4aa3a6ef8e771f180d2a6589c64b0dd5ffebe0aa73703a7256c17d771cd7",
    ),
    (
        "docs/claimgate/biomedical_study.json",
        "9685f2fbafb21477d977dfa0c0bf73e02bea81d084e7605978ea25c47bf5ddce",
    ),
)
_ENGINE = ROOT / "src" / "codontrace" / "genesis" / "engine.py"
_CORE_ENGINE = ROOT / "src" / "codontrace" / "engine.py"
SEEDS = (101, 202, 303, 404, 505)


def test_generator_rejects_non_diagonally_dominant() -> None:
    with pytest.raises(ConfigurationError):
        build_diagonally_dominant_A(5, alpha_off=0.3)
    bad = [[0.2, 0.4, 0.4], [0.4, 0.2, 0.4], [0.4, 0.4, 0.2]]
    with pytest.raises(ConfigurationError):
        assert_diagonally_dominant(bad)


def test_super_host_super_parasite_refused() -> None:
    super_p = [[0.9, 0.05, 0.05], [0.9, 0.05, 0.05], [0.9, 0.05, 0.05]]
    with pytest.raises(ConfigurationError, match="super-parasite"):
        assert_no_super_host_or_parasite(super_p)
    super_h = [[0.05, 0.05, 0.05], [0.5, 0.4, 0.1], [0.4, 0.5, 0.1]]
    with pytest.raises(ConfigurationError, match="super-host"):
        assert_no_super_host_or_parasite(super_h)


def test_canonical_A_is_valid() -> None:
    A = build_diagonally_dominant_A(5)
    assert_diagonally_dominant(A)
    assert_no_super_host_or_parasite(A)
    for row in A:
        assert abs(sum(row) - 1.0) < 1e-9


def test_graded_alpha_from_overlap_bounds() -> None:
    assert graded_alpha_from_overlap([], ["a"]) == pytest.approx(0.01)
    hi = graded_alpha_from_overlap(["a", "b"], ["a"], specialist_bias=0.9)
    lo = graded_alpha_from_overlap(["a"], ["x", "y"], specialist_bias=0.9)
    assert hi > lo
    assert 0.01 <= lo <= hi <= 0.99


def test_graded_repertoire_matrix_diag_dominant() -> None:
    hosts = [["t0"], ["t1"], ["t2"], ["t3"], ["t4"]]
    paras = [["t0"], ["t1"], ["t2"], ["t3"], ["t4"]]
    A = build_graded_A_from_repertoires(hosts, paras)
    assert_diagonally_dominant(A)


def test_capable_defaults_produce_cycling() -> None:
    camp = run_type2_campaign(seeds=SEEDS)
    assert camp["schema"] == SCHEMA
    assert camp["doi"] == "10.1038/srep10004"
    assert camp["pmc"] == "PMC4405699"
    assert camp["red_queen_proved"] is False
    assert camp["n_cycling_seeds"] >= 3
    assert camp["result"] == "SUCCESS"
    # digest stable across processes
    again = run_type2_campaign(seeds=SEEDS)
    assert again["campaign_digest"] == camp["campaign_digest"]


def test_incapable_high_d_fails_honestly() -> None:
    camp = run_type2_campaign(seeds=SEEDS, d=0.40, k=2.0)
    assert camp["n_cycling_seeds"] == 0
    assert camp["result"] == "FAIL"
    assert camp["red_queen_proved"] is False


def test_incapable_tiny_k_fails_honestly() -> None:
    camp = run_type2_campaign(seeds=SEEDS, d=0.12, k=0.5)
    assert camp["n_cycling_seeds"] == 0
    assert camp["result"] == "FAIL"


def test_trial_digest_replay_stable() -> None:
    a = run_type2_cycling_trial(seed=101)
    b = run_type2_cycling_trial(seed=101)
    assert a.trial_digest == b.trial_digest
    assert a.cycling_detected is True


def test_engine_has_no_type2_infection_tokens() -> None:
    for path in (_ENGINE, _CORE_ENGINE):
        text = path.read_text(encoding="utf-8")
        for tok in (
            "build_diagonally_dominant_A",
            "run_type2_cycling_trial",
            "type_II",
            "HostParasiteEnv",
        ):
            assert tok not in text


@pytest.mark.parametrize("path,expected", PIN_SPECS)
def test_baic_pins_intact_type2(path: str, expected: str) -> None:
    digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    assert digest == expected
