"""JR5 phase 1: the prereg record matches its files and the seed blocks are clean."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest

from codontrace.preregistration import PreregistrationRecord
from codontrace.preregistration.manifest import hash_plan

ROOT = Path(__file__).resolve().parents[1]
PREREG_DIR = ROOT / "docs" / "prereg" / "jr5"


def _constants() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((PREREG_DIR / "jr5_prereg_constants.json").read_text(encoding="utf-8"))
    return data


def _record() -> PreregistrationRecord:
    return PreregistrationRecord.from_json((PREREG_DIR / "record.json").read_text(encoding="utf-8"))


def _block(pair: list[int]) -> set[int]:
    lo, hi = pair
    assert lo <= hi
    return set(range(lo, hi + 1))


def test_record_matches_files() -> None:
    rec = _record()
    paths = [p for p, _ in rec.manifest.files]
    fresh = hash_plan(paths, root=ROOT, title=rec.manifest.title)
    assert fresh.files == rec.manifest.files
    assert fresh.digest == rec.manifest.digest


def test_record_covers_constants_and_docs() -> None:
    paths = {p for p, _ in _record().manifest.files}
    for name in (
        "PREREG.md",
        "MATING_TYPES_DESIGN_NOTE.md",
        "SUMMARY_SHA256_NOTE.md",
        "REFERENCES.md",
        "RED_QUEEN_CLAIM_PATH.md",
        "jr5_prereg_constants.json",
    ):
        assert f"docs/prereg/jr5/{name}" in paths


def test_constants_well_formed() -> None:
    c = _constants()
    assert c["schema"] == "codontrace_jr5_prereg_constants_v1"
    assert len(c["base_commit"]) == 40
    assert set(c["typed_outcomes"]) == {
        "rq_consistent",
        "load_consistent",
        "diversity_without_rqd",
        "none",
        "instrument_fail",
    }
    gated = c["gated_claim_flags"]["red_queen_proved"]
    assert gated["default"] is False
    assert len(gated["conditions"]) == 5
    assert (ROOT / gated["doc"]).is_file()
    assert c["host_n"]["primary"] == 200
    assert c["host_n"]["sensitivity"] == 50
    assert c["multiplicity"]["method"] == "holm"


def test_gate_bounds_follow_margin() -> None:
    gate = _constants()["gate_e1"]
    margin = gate["relative_margin"]
    assert gate["alpha"] == 0.05
    assert math.isclose(gate["ci_level"], 1 - 2 * gate["alpha"])
    for s in gate["sex_ratios"]:
        theory = 1.0 / (1.0 - s)
        assert math.isclose(gate["theoretical_cost"][str(s)], theory)
        lo, hi = gate["equivalence_bounds"][str(s)]
        assert math.isclose(lo, (1 - margin) * theory)
        assert math.isclose(hi, (1 + margin) * theory)
        assert lo > gate["must_exclude"]


def test_seed_blocks_do_not_touch_sealed() -> None:
    seeds = _constants()["seeds"]
    sealed: set[int] = set()
    for pair in seeds["sealed_ranges"]:
        sealed |= _block(pair)
    blocks = [_block(seeds[k]) for k in ("confirmatory_block", "e1_calibration_block", "pilot_block")]
    for block in blocks:
        assert not block & sealed
        assert min(block) >= 11001
    for i, a in enumerate(blocks):
        for b in blocks[i + 1 :]:
            assert not a & b


@pytest.mark.parametrize("sealed", [101, 508, 8000, 9601, 9712, 9807])
def test_known_sealed_seeds_listed(sealed: int) -> None:
    ranges = _constants()["seeds"]["sealed_ranges"]
    assert any(lo <= sealed <= hi for lo, hi in ranges)


def test_seed_counts_cover_design() -> None:
    c = _constants()
    conf = _block(c["seeds"]["confirmatory_block"])
    assert len(conf) >= c["e2"]["seeds_per_cell"]
    calib = _block(c["seeds"]["e1_calibration_block"])
    assert len(calib) >= c["gate_e1"]["populations_per_cell"] * len(c["gate_e1"]["sex_ratios"])
