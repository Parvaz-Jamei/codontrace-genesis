"""HE02 paired contrasts. paired_effect_size takes deltas, not two arm vectors."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import replace
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
        except (ConfigurationError, TypeError):
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
    """Confirmatory rule for HE02.

    Passing the statistical rule does **not** raise ClaimGate. This helper
    never returns ``intervention_supported=True``.
    """

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
        "decision_rule_passed": not failures,
        "decision_rule_failures": failures,
        "claim_ceiling": CLAIM_CEILING,
        "intervention_supported": False,
    }


def _committed_results_path() -> Path:
    here = Path(__file__).resolve()
    candidates = []
    if len(here.parents) >= 4:
        candidates.append(here.parents[3] / "docs/hard_experiment_02/results_v1.json")
    candidates.append(Path.cwd() / "docs/hard_experiment_02/results_v1.json")
    for path in candidates:
        if path.is_file():
            return path
    raise ConfigurationError("committed HE02 results_v1.json not found")


def analyze_committed_research(path: Path | None = None) -> dict[str, Any]:
    source = path or _committed_results_path()
    raw = json.loads(source.read_text(encoding="utf-8"))
    contrasts = contrasts_from_seed_dicts(raw["seed_records"], assay_failed=False)
    decision = decision_from_contrasts(contrasts)
    return {
        "source": str(source),
        "source_digest": raw.get("digest"),
        "paired_contrasts": contrasts,
        **decision,
    }


def rescore_he02_campaign(campaign: Any) -> Any:
    """Replace swallowed two-arg ``dz=None`` contrasts on a live campaign."""

    from codontrace.genesis.hard_experiment_02 import HardExperiment02PairedContrast

    rows = contrasts_from_seed_dicts(
        [rec.to_dict() for rec in campaign.seed_records],
        assay_failed=bool(campaign.assay_failed),
    )
    contrasts = tuple(
        HardExperiment02PairedContrast(
            treatment_arm=str(item["treatment_arm"]),
            baseline_arm=str(item["baseline_arm"]),
            dz=item["dz"],
            p_raw=item["p_raw"],
            p_holm=item["p_holm"],
            n_pairs=int(item["n_pairs"]),
        )
        for item in rows
    )
    decision = decision_from_contrasts(rows)
    failures = list(campaign.decision_rule_failures)
    for item in decision["decision_rule_failures"]:
        if item not in failures:
            failures.append(item)
    return replace(
        campaign,
        paired_contrasts=contrasts,
        decision_rule_passed=bool(
            decision["decision_rule_passed"] and not campaign.assay_failed
        ),
        decision_rule_failures=tuple(failures),
        digest="",
    )


def run_hard_experiment_02_v1b(*args: Any, **kwargs: Any) -> Any:
    """Live HE02 run + v1b rescoring. Does not raise ClaimGate."""

    from codontrace.genesis.hard_experiment_02 import run_hard_experiment_02

    return rescore_he02_campaign(run_hard_experiment_02(*args, **kwargs))


def main() -> dict[str, Any]:
    return analyze_committed_research()
