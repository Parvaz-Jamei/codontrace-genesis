"""HE02 paired contrasts. paired_effect_size takes deltas, not two arm vectors."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.hard_experiment_01 import (
    INFERENTIAL_SEED,
    exact_sign_flip_permutation_p,
    holm_correction,
    paired_effect_size,
)

PRIMARY_FIELD = "receiver_mean_terminal_runtime_atp"
BASELINES = ("content_null", "channel_off", "capsules_shuffled")
CLAIM_CEILING = "runtime_observation"


def contrasts_from_seed_dicts(
    seed_records: Sequence[Mapping[str, Any]],
    *,
    assay_failed: bool = False,
) -> list[dict[str, Any]]:
    """Recompute HE02 primary contrasts from frozen seed-row dicts."""

    raw: list[dict[str, Any]] = []
    for baseline in BASELINES:
        deltas: list[float] = []
        for rec in seed_records:
            left = rec["treatment"][PRIMARY_FIELD]
            right = rec[baseline][PRIMARY_FIELD]
            if left is None or right is None:
                continue
            deltas.append(float(left) - float(right))
        if not deltas or assay_failed:
            raw.append(
                {
                    "treatment_arm": "treatment",
                    "baseline_arm": baseline,
                    "dz": None,
                    "p_raw": None,
                    "p_holm": None,
                    "n_pairs": len(deltas),
                }
            )
            continue
        try:
            dz_val = paired_effect_size(deltas) if len(deltas) >= 2 else None
        except ConfigurationError:
            dz_val = None
        p_raw = exact_sign_flip_permutation_p(deltas, seed=INFERENTIAL_SEED)
        raw.append(
            {
                "treatment_arm": "treatment",
                "baseline_arm": baseline,
                "dz": None if dz_val is None else round(float(dz_val), 10),
                "p_raw": round(float(p_raw), 12),
                "p_holm": None,
                "n_pairs": len(deltas),
            }
        )
    p_values = [item["p_raw"] for item in raw]
    if any(value is None for value in p_values):
        return raw
    adjusted = holm_correction([float(value) for value in p_values])
    for item, adj in zip(raw, adjusted, strict=True):
        item["p_holm"] = round(float(adj), 12)
    return raw


def decision_from_contrasts(contrasts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Confirmatory rule for HE02. Does not raise ClaimGate."""

    failures: list[str] = []
    surviving = [
        item
        for item in contrasts
        if item.get("p_holm") is not None
        and float(item["p_holm"]) < 0.05
        and item.get("dz") is not None
        and float(item["dz"]) > 0
    ]
    shuffled = next(
        (item for item in contrasts if item.get("baseline_arm") == "capsules_shuffled"),
        None,
    )
    if (
        shuffled is None
        or shuffled.get("p_holm") is None
        or float(shuffled["p_holm"]) >= 0.05
        or shuffled.get("dz") is None
        or float(shuffled["dz"]) <= 0
    ):
        failures.append("information_control_not_separated")
    if not surviving:
        failures.append("no_holm_surviving_primary_contrast")
    return {
        "decision_rule_passed": False,
        "decision_rule_failures": failures,
        "claim_ceiling": CLAIM_CEILING,
        "intervention_supported": False,
    }


def analyze_committed_research(path: Path | None = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    source = path or (root / "docs/hard_experiment_02/results_v1.json")
    raw = json.loads(source.read_text(encoding="utf-8"))
    contrasts = contrasts_from_seed_dicts(raw["seed_records"], assay_failed=False)
    decision = decision_from_contrasts(contrasts)
    return {
        "source": str(source),
        "source_digest": raw.get("digest"),
        "paired_contrasts": contrasts,
        **decision,
    }


def main() -> None:
    report = analyze_committed_research()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
