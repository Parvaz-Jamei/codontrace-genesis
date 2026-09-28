"""De-toy D3: infection × metabolic-error coupling with dual-null."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_infection_phenotype_coupling import (
    SCHEMA,
    run_infection_phenotype_coupling_campaign,
)

ROOT = Path(__file__).resolve().parents[1]
_ENGINE = ROOT / "src" / "codontrace" / "genesis" / "engine.py"
_CORE = ROOT / "src" / "codontrace" / "engine.py"
PIN_SPECS = (
    (
        "docs/hard_experiment_01/results_v7.json",
        "4a5987c2ed0f09d1088b3c1bca6d81fe2310f3867fa84f22a33fbeee7b5d7efd",
    ),
    (
        "docs/claimgate/risk_bar.json",
        "b7091921bf00c350fa286caf117fa46af81e9760b1b6d4d135eefd042dabd404",
    ),
    (
        "docs/claimgate/biomedical_study.json",
        "2e5193639aad58ceda68ef9bc33943f8eae2c45f042209a060af890c93785079",
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
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
