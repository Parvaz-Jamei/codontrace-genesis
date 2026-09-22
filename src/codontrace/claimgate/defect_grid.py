"""Planted-defect grid and the anti-gaming property.

This is a measurement of the auditor on bundles we built. It is not a
rate for the published in-silico literature.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping

from codontrace.claimgate.auditor import audit_bundle
from codontrace.claimgate.ladder_packs import (
    pack_drop_confirmatory_keep_sensitivity_role,
    pack_empty_limitations,
    pack_identical_arms,
    pack_no_paired_comparison,
    pack_no_replay,
    pack_reference,
    pack_three_seeds,
    pack_zero_width_ci,
)
from codontrace.claimgate.schema import ClaimgateBundle
from codontrace.genesis.canonical import canonical_digest, canonical_payload

# Knockouts that remove a rung the reference bundle had.
SHOULD_DROP: tuple[tuple[str, Callable[[], ClaimgateBundle]], ...] = (
    ("identical_arms", pack_identical_arms),
    ("zero_width_ci", pack_zero_width_ci),
    ("no_paired_comparison", pack_no_paired_comparison),
    ("no_replay", pack_no_replay),
    ("empty_limitations", pack_empty_limitations),
    ("three_seeds", pack_three_seeds),
)

# A sensitivity arm kept under the negative_control role. The auditor
# still sees the role, so this row can stay at the reference level.
NAMED_ESCAPE = ("role_relabel_sensitivity", pack_drop_confirmatory_keep_sensitivity_role)

_LABELS: tuple[Mapping[str, object], ...] = (
    {"model_influence": 3, "decision_consequence": 3, "model_risk": 3},
    {"device_software_kind": "simd_declared", "iec_62304_class": "C", "imdrf_n12_category": "IV"},
    {"fda_2023_evidence": [1, 3, 4, 8], "physics_based": True, "asme_vv40": "passed_label"},
    {"knowledge": "adequate", "importance": "high", "measured": True},
)


def wilson_interval(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval. Successes here are escaped defects."""

    if n < 1:
        raise ValueError("wilson_interval needs at least one trial")
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    margin = z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def _with_labels(bundle: ClaimgateBundle, labels: Mapping[str, object]) -> ClaimgateBundle:
    extra = dict(bundle.extra or {})
    extra.update(labels)
    extra["label_inflation"] = True
    return bundle.__class__(
        software=bundle.software,
        seeds=bundle.seeds,
        config_digest=bundle.config_digest,
        arms=bundle.arms,
        outcomes=bundle.outcomes,
        comparisons=bundle.comparisons,
        replay=bundle.replay,
        artifacts=bundle.artifacts,
        limitations=bundle.limitations,
        preregistration_digest=bundle.preregistration_digest,
        doi=bundle.doi,
        extra=extra,
        schema=bundle.schema,
    )


def anti_gaming_rows(bundle: ClaimgateBundle) -> list[dict[str, object]]:
    """Declared labels must not raise the audited level."""

    base = audit_bundle(bundle).achieved_level
    rows: list[dict[str, object]] = []
    for labels in _LABELS:
        audited = audit_bundle(_with_labels(bundle, labels))
        rows.append(
            {
                "labels": {str(key): labels[key] for key in sorted(labels)},
                "base_level": base,
                "audited_level": audited.achieved_level,
                "raised": audited.achieved_level > base,
            }
        )
    return rows


def defect_grid_payload() -> dict[str, object]:
    reference = audit_bundle(pack_reference()).achieved_level
    rows: list[dict[str, object]] = []
    for name, builder in SHOULD_DROP:
        level = audit_bundle(builder()).achieved_level
        rows.append(
            {
                "defect": name,
                "class": "requirement_knockout",
                "auditor_level": level,
                "escaped": level >= reference,
            }
        )
    escape_name, escape_builder = NAMED_ESCAPE
    escape_level = audit_bundle(escape_builder()).achieved_level
    rows.append(
        {
            "defect": escape_name,
            "class": "role_relabel",
            "auditor_level": escape_level,
            "escaped": escape_level >= reference,
        }
    )
    n = len(rows)
    escaped = sum(1 for row in rows if row["escaped"])
    low, high = wilson_interval(escaped, n)
    gaming = anti_gaming_rows(pack_reference())
    body: dict[str, object] = {
        "schema": "claimgate_defect_grid_v1",
        "reference_level": reference,
        "n_defects": n,
        "n_escaped": escaped,
        "escape_rate": escaped / n,
        "wilson95": [low, high],
        "rows": rows,
        "anti_gaming": gaming,
        "anti_gaming_holds": all(not row["raised"] for row in gaming),
        "population": "planted_defects_on_the_reference_pack",
        "not_a_literature_rate": True,
        "external_raters": False,
    }
    return {**body, "digest": canonical_digest(canonical_payload(body))}
