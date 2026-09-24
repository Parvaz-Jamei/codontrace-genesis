"""De-toy D7: measurement honesty + resource→target dual-null."""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_measurement_resource_target import (
    MEASUREMENT_REFUSED,
    SCHEMA,
    build_measurement_honesty_pack,
    harshness_from_resource,
    run_measurement_resource_target_campaign,
)
from codontrace.genesis.text_digest import sha256_text_file

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
    return run_measurement_resource_target_campaign()


def test_harshness_decreases_with_resource() -> None:
    assert harshness_from_resource(0.4) > harshness_from_resource(2.0)


def test_measurement_pack_refuses_pass_flags() -> None:
    pack = build_measurement_honesty_pack()
    assert pack["tokyo_type1_passed"] is False
    assert pack["modes_passed"] is False
    for name in MEASUREMENT_REFUSED:
        assert pack["flags"][name] is False


def test_campaign_success_and_refuses(camp: dict) -> None:
    assert camp["schema"] == SCHEMA
    assert camp["result"] == "SUCCESS"
    assert camp["metrics"]["slope_ok"] is True
    assert camp["metrics"]["refuse_ok"] is True
    assert camp["metrics"]["mean_intact_delta_low_minus_high"] > 0.0
    assert camp["tokyo_type1_passed"] is False
    assert camp["modes_passed"] is False
    assert camp["red_queen_proved"] is False
    assert camp["intelligence_proved"] is False
    assert camp["collective_intelligence_proved"] is False
    with pytest.raises(ConfigurationError):
        assert_claim_allowed("tokyo_type1_passed")
    with pytest.raises(ConfigurationError):
        assert_claim_allowed("modes_passed")


def test_digest_stable(camp: dict) -> None:
    again = run_measurement_resource_target_campaign()
    assert again["campaign_digest"] == camp["campaign_digest"]


def test_engine_untouched() -> None:
    for path in (_ENGINE, _CORE):
        text = path.read_text(encoding="utf-8")
        assert "measurement_resource_target" not in text
        assert "harshness_from_resource" not in text


@pytest.mark.parametrize("path,expected", PIN_SPECS)
def test_baic_pins_d7(path: str, expected: str) -> None:
    assert sha256_text_file(ROOT / path) == expected
