"""De-toy D3: infection × metabolic-error coupling with dual-null."""

from __future__ import annotations

from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_infection_phenotype_coupling import (
    SCHEMA,
    run_infection_phenotype_coupling_campaign,
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
    return run_infection_phenotype_coupling_campaign()


def test_dual_null_separation(camp: dict) -> None:
    assert camp["schema"] == SCHEMA
    assert camp["result"] == "SUCCESS"
    assert camp["separation_ok"] is True
    assert camp["mean_delta_error"]["intact"] > camp["separation_threshold"]
    assert camp["mean_delta_error"]["content_null"] == pytest.approx(0.0)
    assert camp["mean_delta_error"]["structure_null"] == pytest.approx(0.0)
    assert camp["red_queen_proved"] is False
    assert camp["phage_therapy_cleared"] is False
    assert camp["aevol_identity"] is False
    assert camp["wet_metabolism_claim"] is False
    with pytest.raises(ConfigurationError):
        assert_claim_allowed("phage_therapy_cleared")


def test_digest_stable(camp: dict) -> None:
    again = run_infection_phenotype_coupling_campaign()
    assert again["campaign_digest"] == camp["campaign_digest"]


def test_engine_untouched() -> None:
    for path in (_ENGINE, _CORE):
        text = path.read_text(encoding="utf-8")
        assert "decode_abstract_phenotype" not in text
        assert "infection_phenotype_coupling" not in text
        assert "HostParasiteEnv" not in text


@pytest.mark.parametrize("path,expected", PIN_SPECS)
def test_baic_pins_d3(path: str, expected: str) -> None:
    assert sha256_text_file(ROOT / path) == expected
