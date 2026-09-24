"""De-toy D6: type-III phase-locked rare panel (SF9-candidate)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_type3_rare_lock import (
    PANEL_ID,
    SCHEMA,
    run_type3_rare_lock_campaign,
    run_type3_rare_lock_trial,
    type3_functional_response,
)

ROOT = Path(__file__).resolve().parents[1]
_ENGINE = ROOT / "src" / "codontrace" / "genesis" / "engine.py"
_CORE = ROOT / "src" / "codontrace" / "engine.py"
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


@pytest.fixture(scope="module")
def camp() -> dict:
    return run_type3_rare_lock_campaign()


def test_type3_fr_sigmoidal_shape() -> None:
    lo = type3_functional_response(1.0, 1.0, c=8.0)
    mid = type3_functional_response(8.0, 1.0, c=8.0)
    hi = type3_functional_response(40.0, 1.0, c=8.0)
    assert lo < mid < hi
    assert hi < 1.0


def test_sf9_success_separate_from_sf4(camp: dict) -> None:
    assert camp["schema"] == SCHEMA
    assert camp["panel_id"] == PANEL_ID
    assert camp["result"] == "SUCCESS"
    assert camp["n_sf9_pattern_seeds"] >= 3
    assert camp["soft_passes_sf4"] is False
    assert camp["sf4_result_unchanged_by_this_panel"] is True
    assert camp["red_queen_proved"] is False
    assert camp["doi"] == "10.1126/sciadv.1501548"
    assert camp["type2_ablation_suppresses_pattern"] is True
    assert camp["n_type2_ablation_sf9_seeds"] <= 1
    with pytest.raises(ConfigurationError):
        assert_claim_allowed("red_queen_proved")


def test_success_cannot_set_red_queen_proved(camp: dict) -> None:
    assert camp["result"] == "SUCCESS"
    assert camp["red_queen_proved"] is False
    for t in camp["intact_trials"]:
        assert t["red_queen_proved"] is False
        assert t["soft_passes_sf4"] is False


def test_digest_stable(camp: dict) -> None:
    again = run_type3_rare_lock_campaign()
    assert again["campaign_digest"] == camp["campaign_digest"]


def test_engine_untouched() -> None:
    for path in (_ENGINE, _CORE):
        text = path.read_text(encoding="utf-8")
        assert "type3_rare_lock" not in text
        assert "type3_functional_response" not in text
        assert "HostParasiteEnv" not in text


@pytest.mark.parametrize("path,expected", PIN_SPECS)
def test_baic_pins_d6(path: str, expected: str) -> None:
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected


def test_single_trial_type2_ablation_differs() -> None:
    iii = run_type3_rare_lock_trial(seed=101, fr_mode="type_III")
    ii = run_type3_rare_lock_trial(seed=101, fr_mode="type_II")
    assert iii.sf9_pattern is True
    assert ii.to_dict()["soft_passes_sf4"] is False
    assert ii.to_dict()["red_queen_proved"] is False
