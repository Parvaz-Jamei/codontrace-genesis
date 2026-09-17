"""Lock HE02 analysis v1b against frozen research ATP rows."""

from __future__ import annotations

import json
from pathlib import Path

from codontrace.genesis.he02_contrasts import contrasts_from_seed_dicts


def test_he02_v1b_contrasts_match_frozen_rows() -> None:
    root = Path(__file__).resolve().parents[1]
    raw = json.loads((root / "docs/hard_experiment_02/results_v1.json").read_text())
    expected = json.loads(
        (root / "docs/hard_experiment_02/analysis_v1b_contrasts.json").read_text()
    )
    computed = contrasts_from_seed_dicts(raw["seed_records"], assay_failed=False)
    assert expected["source_digest"] == raw["digest"]
    assert expected["claim_ceiling"] == "runtime_observation"
    assert computed == expected["paired_contrasts"]
    shuffled = next(item for item in computed if item["baseline_arm"] == "capsules_shuffled")
    assert shuffled["p_holm"] is not None and float(shuffled["p_holm"]) >= 0.05
