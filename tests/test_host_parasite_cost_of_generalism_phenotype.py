"""De-toy D5: cost-of-generalism on abstract phenotype + dual-null."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_cost_of_generalism_phenotype import (
    SCHEMA,
    generalism_phenotype_penalty,
    repertoire_shannon_entropy,
    run_cost_of_generalism_phenotype_campaign,
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
    return run_cost_of_generalism_phenotype_campaign()


def test_entropy_generalist_gt_specialist() -> None:
    g = repertoire_shannon_entropy(("a", "b", "c", "d", "e"))
    s = repertoire_shannon_entropy(("a",))
    assert g > s
    assert generalism_phenotype_penalty(("a", "b", "c", "d", "e")) > generalism_phenotype_penalty(
        ("a",)
    )


def test_campaign_success_and_refuses(camp: dict) -> None:
    assert camp["schema"] == SCHEMA
    assert camp["result"] == "SUCCESS"
    assert camp["metrics"]["dual_null_ok"] is True
    assert camp["metrics"]["coexistence_contrast_ok"] is True
    assert camp["metrics"]["cost_on_coexistence_seeds"] >= 3
    assert camp["metrics"]["cost_off_collapse_or_dominance_seeds"] >= 3
    assert camp["red_queen_proved"] is False
    assert camp["wet_ard_fsd_identity"] is False
    assert camp["phage_therapy_cleared"] is False
    assert camp["doi_primary"] == "10.1098/rspb.2012.0769"
    with pytest.raises(ConfigurationError):
        assert_claim_allowed("phage_therapy_cleared")


def test_digest_stable(camp: dict) -> None:
    again = run_cost_of_generalism_phenotype_campaign()
    assert again["campaign_digest"] == camp["campaign_digest"]


def test_engine_untouched() -> None:
    for path in (_ENGINE, _CORE):
        text = path.read_text(encoding="utf-8")
        assert "cost_of_generalism_phenotype" not in text
        assert "generalism_phenotype_penalty" not in text
        assert "HostParasiteEnv" not in text


@pytest.mark.parametrize("path,expected", PIN_SPECS)
def test_baic_pins_d5(path: str, expected: str) -> None:
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
