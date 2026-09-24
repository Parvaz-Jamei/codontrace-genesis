"""De-toy D2: d × K region map tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from codontrace.claimgate.adapters.host_parasite import assert_claim_allowed
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_dk_region_map import (
    SCHEMA,
    run_dk_region_map,
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


@pytest.fixture(scope="module")
def region_map() -> dict:
    return run_dk_region_map()


def test_region_map_schema_and_refuses(region_map: dict) -> None:
    assert region_map["schema"] == SCHEMA
    assert region_map["domain_profile"] == "host_parasite"
    assert region_map["doi"] == "10.1038/srep10004"
    assert region_map["red_queen_proved"] is False
    assert region_map["clinical_prediction_refused"] is True
    assert region_map["n_cells"] == 20
    assert len(region_map["map_digest"]) == 64
    with pytest.raises(ConfigurationError):
        assert_claim_allowed("red_queen_proved")


def test_capable_region_nonempty_extremes_empty(region_map: dict) -> None:
    assert region_map["n_cycling_capable_cells"] >= 1
    assert region_map["prereg_pattern_matched"] is True
    assert region_map["mid_d_high_k_capable_count"] >= 1
    assert region_map["tiny_k_capable_count"] <= 1
    # Spot-check known cells
    by = {(c["d"], c["K"]): c for c in region_map["cells"]}
    assert by[(0.12, 2.0)]["label"] == "cycling_capable"
    assert by[(0.12, 0.5)]["label"] == "noncycling"
    # Honesty: coarser epoch metric may exceed Sci Rep visual RQ at edges.
    assert "mismatch" in region_map["prereg_pattern_note"] or region_map[
        "sci_rep_visual_exact_match"
    ]


def test_digest_stable(region_map: dict) -> None:
    again = run_dk_region_map()
    assert again["map_digest"] == region_map["map_digest"]


@pytest.mark.parametrize("path,expected", PIN_SPECS)
def test_baic_pins_intact_d2(path: str, expected: str) -> None:
    digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    assert digest == expected
