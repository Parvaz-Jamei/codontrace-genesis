"""Lock HE02 analysis v1b against frozen research ATP rows."""

from __future__ import annotations

import json
from pathlib import Path

from codontrace.genesis.hard_experiment_01 import (
    INFERENTIAL_SEED,
    exact_sign_flip_permutation_p,
    holm_correction,
    paired_effect_size,
)


def test_he02_v1b_contrasts_match_frozen_rows() -> None:
    root = Path(__file__).resolve().parents[1]
    raw = json.loads((root / "docs/hard_experiment_02/results_v1.json").read_text())
    expected = json.loads(
        (root / "docs/hard_experiment_02/analysis_v1b_contrasts.json").read_text()
    )
    computed = []
    p_raws: list[float] = []
    for baseline in ("content_null", "channel_off", "capsules_shuffled"):
        deltas = [
            float(rec["treatment"]["receiver_mean_terminal_runtime_atp"])
            - float(rec[baseline]["receiver_mean_terminal_runtime_atp"])
            for rec in raw["seed_records"]
        ]
        dz = paired_effect_size(deltas)
        p_raw = exact_sign_flip_permutation_p(deltas, seed=INFERENTIAL_SEED)
        p_raws.append(p_raw)
        computed.append(
            {
                "treatment_arm": "treatment",
                "baseline_arm": baseline,
                "dz": round(float(dz), 10),
                "p_raw": round(float(p_raw), 12),
                "n_pairs": len(deltas),
            }
        )
    holm = holm_correction(p_raws)
    for item, adj in zip(computed, holm, strict=True):
        item["p_holm"] = round(float(adj), 12)
    assert expected["source_digest"] == raw["digest"]
    assert expected["claim_ceiling"] == "runtime_observation"
    assert computed == expected["paired_contrasts"]
    shuffled = next(item for item in computed if item["baseline_arm"] == "capsules_shuffled")
    assert float(shuffled["p_holm"]) >= 0.05
